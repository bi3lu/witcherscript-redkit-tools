import * as cp from "node:child_process";
import * as path from "node:path";
import * as vscode from "vscode";
import {
  LanguageClient,
  LanguageClientOptions,
  ServerOptions,
} from "vscode-languageclient/node";

const CONFIG_SECTION = "witcherscript";
const REFRESH_INDEX_COMMAND = "witcherscript.refreshIndex";
const REDKIT_INIT_COMMAND = "witcherscript.redkitInit";
const RESTART_SERVER_COMMAND = "witcherscript.restartLanguageServer";

let client: LanguageClient | undefined;
let outputChannel: vscode.OutputChannel | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  outputChannel = vscode.window.createOutputChannel("WitcherScript");
  context.subscriptions.push(outputChannel);

  context.subscriptions.push(
    vscode.commands.registerCommand(REFRESH_INDEX_COMMAND, async () => {
      await refreshIndex();
    }),
    vscode.commands.registerCommand(REDKIT_INIT_COMMAND, async () => {
      await initializeRedkitConfig(context);
    }),
    vscode.commands.registerCommand(RESTART_SERVER_COMMAND, async () => {
      await restartLanguageServer(context);
    }),
  );

  await startLanguageServer(context);
}

export async function deactivate(): Promise<void> {
  await stopLanguageServer();
}

async function startLanguageServer(context: vscode.ExtensionContext): Promise<void> {
  if (client !== undefined) {
    return;
  }

  const workspaceFolder = currentWorkspaceFolder();
  const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
  const command = config.get<string>("languageServer.command", "uv");
  const args = config.get<string[]>("languageServer.args", ["run", "witcherscript-lsp"]);
  const cwd = expandPath(
    config.get<string>("languageServer.cwd", "${workspaceFolder}"),
    context,
    workspaceFolder,
  );

  const serverOptions: ServerOptions = {
    command,
    args: args.map((argument) => expandPath(argument, context, workspaceFolder)),
    options: {
      cwd,
    },
  };
  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "witcherscript" }],
    outputChannel,
    synchronize: {
      fileEvents: [
        vscode.workspace.createFileSystemWatcher("**/*.ws"),
        vscode.workspace.createFileSystemWatcher("**/witcherscript.toml"),
      ],
    },
  };

  client = new LanguageClient(
    "witcherscript",
    "WitcherScript Language Server",
    serverOptions,
    clientOptions,
  );

  context.subscriptions.push(client);
  outputChannel?.appendLine(`Starting WitcherScript LSP: ${command} ${args.join(" ")}`);
  await client.start();
}

async function stopLanguageServer(): Promise<void> {
  const runningClient = client;
  client = undefined;

  if (runningClient !== undefined) {
    await runningClient.stop();
  }
}

async function restartLanguageServer(context: vscode.ExtensionContext): Promise<void> {
  await stopLanguageServer();
  await startLanguageServer(context);
  vscode.window.showInformationMessage("WitcherScript language server restarted.");
}

async function refreshIndex(): Promise<void> {
  if (client === undefined) {
    vscode.window.showWarningMessage("WitcherScript language server is not running.");
    return;
  }

  const result = await client.sendRequest<RefreshIndexResult>("workspace/executeCommand", {
    command: REFRESH_INDEX_COMMAND,
    arguments: [],
  });

  if (result === null || result === undefined) {
    vscode.window.showInformationMessage("WitcherScript project index refreshed.");
    return;
  }

  vscode.window.showInformationMessage(
    `WitcherScript index refreshed: ${result.indexedFiles} file(s), ${result.indexedSymbols} symbol(s).`,
  );
}

async function initializeRedkitConfig(context: vscode.ExtensionContext): Promise<void> {
  const workspaceFolder = currentWorkspaceFolder();

  if (workspaceFolder === undefined) {
    vscode.window.showWarningMessage("Open a workspace folder before initializing REDkit config.");
    return;
  }

  const { command, args } = redkitCommand(context, workspaceFolder);

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Initializing WitcherScript REDkit configuration",
    },
    async () => {
      await executeRedkitCommand(command, [
        ...args,
        "init",
        "--project-dir",
        workspaceFolder.uri.fsPath,
      ]);
    },
  );

  await refreshIndex();
}

function executeRedkitCommand(command: string, args: string[]): Promise<void> {
  outputChannel?.appendLine(`Running REDkit tooling: ${command} ${args.join(" ")}`);

  return new Promise((resolve, reject) => {
    cp.execFile(command, args, { windowsHide: true }, (error, stdout, stderr) => {
      if (stdout.length > 0) {
        outputChannel?.append(stdout);
      }

      if (stderr.length > 0) {
        outputChannel?.append(stderr);
      }

      if (error !== null) {
        outputChannel?.show(true);
        vscode.window.showErrorMessage(`REDkit config initialization failed: ${error.message}`);
        reject(error);
        return;
      }

      vscode.window.showInformationMessage("WitcherScript REDkit config initialized.");
      resolve();
    });
  });
}

function redkitCommand(
  context: vscode.ExtensionContext,
  workspaceFolder: vscode.WorkspaceFolder,
): CommandLine {
  const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
  const command = config.get<string>("redkit.command", "dotnet");
  const configuredArgs = config.get<string[]>("redkit.args", []);

  if (configuredArgs.length > 0) {
    return {
      command,
      args: configuredArgs.map((argument) => expandPath(argument, context, workspaceFolder)),
    };
  }

  if (command !== "dotnet") {
    return {
      command,
      args: [],
    };
  }

  const cliProject = path.join(
    context.extensionPath,
    "..",
    "dotnet",
    "src",
    "WitcherScript.RedkitTooling.Cli",
    "WitcherScript.RedkitTooling.Cli.csproj",
  );

  return {
    command,
    args: ["run", "--project", cliProject, "--"],
  };
}

function currentWorkspaceFolder(): vscode.WorkspaceFolder | undefined {
  const activeDocument = vscode.window.activeTextEditor?.document;

  if (activeDocument !== undefined) {
    const folder = vscode.workspace.getWorkspaceFolder(activeDocument.uri);

    if (folder !== undefined) {
      return folder;
    }
  }

  return vscode.workspace.workspaceFolders?.[0];
}

function expandPath(
  value: string,
  context: vscode.ExtensionContext,
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): string {
  return value
    .replaceAll("${extensionPath}", context.extensionPath)
    .replaceAll("${workspaceFolder}", workspaceFolder?.uri.fsPath ?? "");
}

interface RefreshIndexResult {
  indexedFiles: number;
  indexedSymbols: number;
}

interface CommandLine {
  command: string;
  args: string[];
}
