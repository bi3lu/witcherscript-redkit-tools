import * as cp from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";
import { LanguageClient, State } from "vscode-languageclient/node";
import type { LanguageClientOptions, ServerOptions } from "vscode-languageclient/node";

const CONFIG_SECTION = "witcherscript";
const REFRESH_INDEX_COMMAND = "witcherscript.refreshIndex";
const REDKIT_INIT_COMMAND = "witcherscript.redkitInit";
const REDKIT_RECOMPILE_COMMAND = "witcherscript.redkitRecompile";
const REDKIT_LAUNCH_GAME_COMMAND = "witcherscript.redkitLaunchGame";
const RESTART_SERVER_COMMAND = "witcherscript.restartLanguageServer";
const SHOW_OUTPUT_COMMAND = "witcherscript.showOutput";

let client: LanguageClient | undefined;
let outputChannel: vscode.OutputChannel | undefined;
let statusBarItem: vscode.StatusBarItem | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  outputChannel = vscode.window.createOutputChannel("WitcherScript");
  context.subscriptions.push(outputChannel);
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  statusBarItem.command = SHOW_OUTPUT_COMMAND;
  statusBarItem.tooltip = "WitcherScript Language Server";
  context.subscriptions.push(statusBarItem);
  updateStatus("stopped");

  context.subscriptions.push(
    vscode.commands.registerCommand(SHOW_OUTPUT_COMMAND, () => {
      outputChannel?.show(true);
    }),
    vscode.commands.registerCommand(REFRESH_INDEX_COMMAND, async () => {
      await refreshIndex();
    }),
    vscode.commands.registerCommand(REDKIT_INIT_COMMAND, async () => {
      await initializeRedkitConfig(context);
    }),
    vscode.commands.registerCommand(REDKIT_RECOMPILE_COMMAND, async () => {
      await recompileRedkitScripts(context);
    }),
    vscode.commands.registerCommand(REDKIT_LAUNCH_GAME_COMMAND, async () => {
      await launchGame(context);
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

  const workspaceFolder = effectiveWorkspaceFolder(context);
  const serverCommand = languageServerCommand(context, workspaceFolder);

  const serverOptions: ServerOptions = {
    command: serverCommand.command,
    args: serverCommand.args,
    options: {
      cwd: serverCommand.cwd,
    },
  };
  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", language: "witcherscript" }],
    outputChannel,
    workspaceFolder,
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

  client.onDidChangeState((event) => {
    updateStatus(stateToStatus(event.newState));
  });
  context.subscriptions.push(client);
  outputChannel?.appendLine(
    `Starting WitcherScript LSP: ${serverCommand.command} ${serverCommand.args.join(" ")}`,
  );
  outputChannel?.appendLine(`LSP working directory: ${serverCommand.cwd}`);
  outputChannel?.appendLine(`Workspace root: ${workspaceFolder?.uri.fsPath ?? "<none>"}`);
  updateStatus("starting");

  try {
    await client.start();
    updateStatus("running");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    client = undefined;
    updateStatus("error", "start failed");
    outputChannel?.appendLine(`Failed to start WitcherScript LSP: ${message}`);
    await showStartupError(message, serverCommand);
  }
}

async function stopLanguageServer(): Promise<void> {
  const runningClient = client;
  client = undefined;

  if (runningClient !== undefined) {
    updateStatus("stopping");
    try {
      await runningClient.stop();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      outputChannel?.appendLine(`Failed to stop WitcherScript LSP cleanly: ${message}`);
    }
  }

  updateStatus("stopped");
}

async function restartLanguageServer(context: vscode.ExtensionContext): Promise<void> {
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Window,
      title: "Restarting WitcherScript language server",
    },
    async () => {
      await stopLanguageServer();
      await startLanguageServer(context);
    },
  );

  if (client !== undefined) {
    vscode.window.showInformationMessage("WitcherScript language server restarted.");
  }
}

async function refreshIndex(): Promise<void> {
  if (client === undefined) {
    vscode.window.showWarningMessage("WitcherScript language server is not running.");
    return;
  }

  updateStatus("indexing");
  let result: RefreshIndexResult | null | undefined;

  try {
    result = await client.sendRequest<RefreshIndexResult>("workspace/executeCommand", {
      command: REFRESH_INDEX_COMMAND,
      arguments: [],
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    updateStatus("error", "refresh failed");
    outputChannel?.appendLine(`Refresh index failed: ${message}`);
    vscode.window.showErrorMessage(`WitcherScript index refresh failed: ${message}`);
    return;
  }

  updateStatus("running");

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
  const configPath = vscode.Uri.file(path.join(workspaceFolder.uri.fsPath, "witcherscript.toml"));
  const commandArgs = [
    ...args,
    "init",
    "--project-dir",
    workspaceFolder.uri.fsPath,
  ];

  if (await fileExists(configPath)) {
    const action = await vscode.window.showWarningMessage(
      "witcherscript.toml already exists in this workspace.",
      { modal: true },
      "Overwrite",
    );

    if (action !== "Overwrite") {
      return;
    }

    commandArgs.push("--force");
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Initializing WitcherScript REDkit configuration",
    },
    async () => {
      await executeRedkitCommand(
        command,
        commandArgs,
        "REDkit config initialization",
        "WitcherScript REDkit config initialized.",
      );
    },
  );

  await refreshIndex();
}

async function fileExists(uri: vscode.Uri): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

async function recompileRedkitScripts(context: vscode.ExtensionContext): Promise<void> {
  const workspaceFolder = currentWorkspaceFolder();

  if (workspaceFolder === undefined) {
    vscode.window.showWarningMessage("Open a workspace folder before recompiling scripts.");
    return;
  }

  const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
  const executable = expandPath(
    config.get<string>("redkit.recompile.executable", ""),
    context,
    workspaceFolder,
  ).trim();

  if (executable.length === 0) {
    const action = await vscode.window.showErrorMessage(
      "Configure witcherscript.redkit.recompile.executable before running script recompilation.",
      "Open Settings",
    );

    if (action === "Open Settings") {
      await vscode.commands.executeCommand(
        "workbench.action.openSettings",
        "witcherscript.redkit.recompile.executable",
      );
    }

    return;
  }

  const { command, args } = redkitCommand(context, workspaceFolder);
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Recompiling WitcherScript scripts",
    },
    async () => {
      await executeRedkitCommand(
        command,
        [
          ...args,
          "recompile",
          "--project-dir",
          workspaceFolder.uri.fsPath,
          "--executable",
          executable,
        ],
        "REDkit script recompilation",
        "WitcherScript scripts recompiled.",
      );
    },
  );
}

async function launchGame(context: vscode.ExtensionContext): Promise<void> {
  const workspaceFolder = currentWorkspaceFolder();

  if (workspaceFolder === undefined) {
    vscode.window.showWarningMessage("Open a workspace folder before launching the game.");
    return;
  }

  const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
  const executable = expandPath(
    config.get<string>("redkit.launch.executable", ""),
    context,
    workspaceFolder,
  ).trim();
  const launchArgs = config
    .get<string[]>("redkit.launch.args", [])
    .map((argument) => expandPath(argument, context, workspaceFolder));
  const { command, args } = redkitCommand(context, workspaceFolder);
  const commandArgs = [
    ...args,
    "launch-game",
    "--project-dir",
    workspaceFolder.uri.fsPath,
  ];

  if (executable.length > 0) {
    commandArgs.push("--executable", executable);
  }

  if (launchArgs.length > 0) {
    commandArgs.push("--", ...launchArgs);
  }

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Launching The Witcher 3",
    },
    async () => {
      await executeRedkitCommand(
        command,
        commandArgs,
        "REDkit game launch",
        "The Witcher 3 launched.",
      );
    },
  );
}

function executeRedkitCommand(
  command: string,
  args: string[],
  label: string,
  successMessage: string,
): Promise<void> {
  outputChannel?.appendLine(`Running REDkit tooling: ${command} ${args.join(" ")}`);

  return new Promise((resolve, reject) => {
    cp.execFile(
      command,
      args,
      { maxBuffer: 1024 * 1024 * 8, windowsHide: true },
      (error, stdout, stderr) => {
        if (stdout.length > 0) {
          outputChannel?.append(stdout);
        }

        if (stderr.length > 0) {
          outputChannel?.append(stderr);
        }

        if (error !== null) {
          outputChannel?.show(true);
          vscode.window.showErrorMessage(`${label} failed: ${error.message}`);
          reject(new Error(error.message, { cause: error }));
          return;
        }

        vscode.window.showInformationMessage(successMessage);
        resolve();
      },
    );
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

  const cliProject = bundledRedkitCliProject(context);

  return {
    command,
    args: ["run", "--project", cliProject, "--"],
  };
}

function languageServerCommand(
  context: vscode.ExtensionContext,
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): LanguageServerCommand {
  const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
  const executablePath = expandPath(
    config.get<string>("languageServer.path", ""),
    context,
    workspaceFolder,
  ).trim();
  const configuredCommand = config.get<string>("languageServer.command", "uv");
  const command =
    executablePath.length > 0
      ? executablePath
      : expandPath(configuredCommand, context, workspaceFolder);
  const args = config
    .get<string[]>("languageServer.args", ["run", "witcherscript-lsp"])
    .map((argument) => expandPath(argument, context, workspaceFolder));
  const configuredCwd = expandPath(
    config.get<string>("languageServer.cwd", ""),
    context,
    workspaceFolder,
  ).trim();
  const cwd = configuredCwd.length > 0 ? configuredCwd : defaultLanguageServerCwd(context);

  return {
    command,
    args,
    cwd,
  };
}

function defaultLanguageServerCwd(context: vscode.ExtensionContext): string {
  const bundledServer = path.join(context.extensionPath, "server");

  if (pathExists(bundledServer)) {
    return bundledServer;
  }

  return path.resolve(context.extensionPath, "..", "..");
}

function bundledRedkitCliProject(context: vscode.ExtensionContext): string {
  const bundledProject = path.join(
    context.extensionPath,
    "redkit",
    "src",
    "WitcherScript.RedkitTooling.Cli",
    "WitcherScript.RedkitTooling.Cli.csproj",
  );

  if (pathExists(bundledProject)) {
    return bundledProject;
  }

  return path.join(
    context.extensionPath,
    "..",
    "dotnet",
    "src",
    "WitcherScript.RedkitTooling.Cli",
    "WitcherScript.RedkitTooling.Cli.csproj",
  );
}

function pathExists(candidate: string): boolean {
  try {
    return fs.existsSync(candidate);
  } catch {
    return false;
  }
}

function effectiveWorkspaceFolder(
  context: vscode.ExtensionContext,
): vscode.WorkspaceFolder | undefined {
  const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
  const configuredRoot = expandPath(
    config.get<string>("workspace.root", "${workspaceFolder}"),
    context,
    currentWorkspaceFolder(),
  ).trim();

  if (configuredRoot.length > 0) {
    const rootUri = vscode.Uri.file(configuredRoot);

    return {
      uri: rootUri,
      name: path.basename(rootUri.fsPath),
      index: 0,
    };
  }

  return currentWorkspaceFolder();
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
    outputChannel?.show(true);
  }

  if (action === "Open Settings") {
    await vscode.commands.executeCommand(
      "workbench.action.openSettings",
      "@ext:witcherscript.witcherscript-redkit-tools languageServer",
    );
  }
}

function updateStatus(status: LspStatus, detail?: string): void {
  if (statusBarItem === undefined) {
    return;
  }

  const label =
    detail === undefined ? STATUS_LABELS[status] : `${STATUS_LABELS[status]} (${detail})`;
  statusBarItem.text = label;
  statusBarItem.tooltip = `WitcherScript Language Server: ${status}`;
  statusBarItem.show();
}

function stateToStatus(state: State): LspStatus {
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

const STATUS_LABELS: Record<LspStatus, string> = {
  error: "$(error) WitcherScript",
  indexing: "$(sync~spin) WitcherScript",
  running: "$(check) WitcherScript",
  starting: "$(loading~spin) WitcherScript",
  stopped: "$(circle-slash) WitcherScript",
  stopping: "$(loading~spin) WitcherScript",
};

type LspStatus = "error" | "indexing" | "running" | "starting" | "stopped" | "stopping";

interface RefreshIndexResult {
  indexedFiles: number;
  indexedSymbols: number;
}

interface CommandLine {
  command: string;
  args: string[];
}

interface LanguageServerCommand extends CommandLine {
  cwd: string;
}
