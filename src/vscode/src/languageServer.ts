import * as vscode from "vscode";
import { LanguageClient, State } from "vscode-languageclient/node";
import type { LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";
import { REFRESH_INDEX_COMMAND } from "./constants";
import { effectiveWorkspaceFolder, languageServerCommand } from "./configuration";
import type { WitcherScriptStatusBar } from "./statusBar";
import type { LanguageServerCommand } from "./types";

export class LanguageServerController {
  private client: LanguageClient | undefined;

  public constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly outputChannel: vscode.OutputChannel,
    private readonly statusBar: WitcherScriptStatusBar,
  ) {}

  public get state(): State | undefined {
    return this.client?.state;
  }

  public async start(): Promise<void> {
    if (this.client !== undefined) {
      return;
    }

    const workspaceFolder = effectiveWorkspaceFolder(this.context);
    const serverCommand = languageServerCommand(this.context, workspaceFolder);
    const serverOptions: ServerOptions = {
      command: serverCommand.command,
      args: serverCommand.args,
      options: {
        cwd: serverCommand.cwd,
      },
    };
    const clientOptions: LanguageClientOptions = {
      documentSelector: [{ scheme: "file", language: "witcherscript" }],
      outputChannel: this.outputChannel,
      workspaceFolder,
      synchronize: {
        fileEvents: [
          vscode.workspace.createFileSystemWatcher("**/*.ws"),
          vscode.workspace.createFileSystemWatcher("**/witcherscript.toml"),
        ],
      },
    };

    this.client = new LanguageClient(
      "witcherscript",
      "WitcherScript Language Server",
      serverOptions,
      clientOptions,
    );
    this.client.onDidChangeState((event) => {
      this.statusBar.update(stateToStatus(event.newState));
    });
    this.context.subscriptions.push(this.client);
    this.outputChannel.appendLine(
      `Starting WitcherScript LSP: ${serverCommand.command} ${serverCommand.args.join(" ")}`,
    );
    this.outputChannel.appendLine(`LSP working directory: ${serverCommand.cwd}`);
    this.outputChannel.appendLine(`Workspace root: ${workspaceFolder?.uri.fsPath ?? "<none>"}`);
    this.statusBar.update("starting");

    try {
      await this.client.start();
      this.statusBar.update("running");
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.client = undefined;
      this.statusBar.update("error", "start failed");
      this.outputChannel.appendLine(`Failed to start WitcherScript LSP: ${message}`);
      await showStartupError(message, serverCommand);
    }
  }

  public async stop(): Promise<void> {
    const runningClient = this.client;
    this.client = undefined;

    if (runningClient !== undefined) {
      this.statusBar.update("stopping");
      try {
        await runningClient.stop();
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        this.outputChannel.appendLine(`Failed to stop WitcherScript LSP cleanly: ${message}`);
      }
    }

    this.statusBar.update("stopped");
  }

  public async restart(): Promise<void> {
    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Window,
        title: "Restarting WitcherScript language server",
      },
      async () => {
        await this.stop();
        await this.start();
      },
    );

    if (this.client !== undefined) {
      vscode.window.showInformationMessage("WitcherScript language server restarted.");
    }
  }

  public async refreshIndex(): Promise<void> {
    if (this.client === undefined) {
      vscode.window.showWarningMessage("WitcherScript language server is not running.");
      return;
    }

    this.statusBar.update("indexing");
    let result: RefreshIndexResult | null | undefined;

    try {
      result = await this.client.sendRequest<RefreshIndexResult>("workspace/executeCommand", {
        command: REFRESH_INDEX_COMMAND,
        arguments: [],
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      this.statusBar.update("error", "refresh failed");
      this.outputChannel.appendLine(`Refresh index failed: ${message}`);
      vscode.window.showErrorMessage(`WitcherScript index refresh failed: ${message}`);
      return;
    }

    this.statusBar.update("running");

    if (result === null || result === undefined) {
      vscode.window.showInformationMessage("WitcherScript project index refreshed.");
      return;
    }

    vscode.window.showInformationMessage(
      `WitcherScript index refreshed: ${result.indexedFiles} file(s), ${result.indexedSymbols} symbol(s).`,
    );
  }
}

function stateToStatus(state: State): "running" | "starting" | "stopped" {
  switch (state) {
    case State.Starting:
      return "starting";
    case State.Running:
      return "running";
    case State.Stopped:
      return "stopped";
    default:
      return "stopped";
  }
}

async function showStartupError(
  message: string,
  serverCommand: LanguageServerCommand,
): Promise<void> {
  const action = await vscode.window.showErrorMessage(
    [
      "WitcherScript language server failed to start.",
      `Command: ${serverCommand.command} ${serverCommand.args.join(" ")}`,
      `CWD: ${serverCommand.cwd}`,
      `Error: ${message}`,
    ].join("\n"),
    "Open Logs",
    "Open Settings",
  );

  if (action === "Open Logs") {
    await vscode.commands.executeCommand("witcherscript.showOutput");
  }

  if (action === "Open Settings") {
    await vscode.commands.executeCommand(
      "workbench.action.openSettings",
      "@ext:witcherscript.witcherscript-redkit-tools languageServer",
    );
  }
}

interface RefreshIndexResult {
  indexedFiles: number;
  indexedSymbols: number;
}
