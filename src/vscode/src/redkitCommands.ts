import * as cp from "node:child_process";
import * as vscode from "vscode";
import { CONFIG_SECTION } from "./constants";
import { redkitCommand } from "./configuration";
import { currentWorkspaceFolder, expandPath, fileExists, workspaceConfigUri } from "./paths";

export async function initializeRedkitConfig(
  context: vscode.ExtensionContext,
  outputChannel: vscode.OutputChannel,
  refreshIndex: () => Promise<void>,
): Promise<void> {
  const workspaceFolder = currentWorkspaceFolder();

  if (workspaceFolder === undefined) {
    vscode.window.showWarningMessage("Open a workspace folder before initializing REDkit config.");
    return;
  }

  const { command, args } = redkitCommand(context, workspaceFolder);
  const configPath = workspaceConfigUri(workspaceFolder);
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
        outputChannel,
      );
    },
  );

  await refreshIndex();
}

export async function recompileRedkitScripts(
  context: vscode.ExtensionContext,
  outputChannel: vscode.OutputChannel,
): Promise<void> {
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
        outputChannel,
      );
    },
  );
}

export async function launchGame(
  context: vscode.ExtensionContext,
  outputChannel: vscode.OutputChannel,
): Promise<void> {
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
        outputChannel,
      );
    },
  );
}

function executeRedkitCommand(
  command: string,
  args: string[],
  label: string,
  successMessage: string,
  outputChannel: vscode.OutputChannel,
): Promise<void> {
  outputChannel.appendLine(`Running REDkit tooling: ${command} ${args.join(" ")}`);

  return new Promise((resolve, reject) => {
    cp.execFile(
      command,
      args,
      { maxBuffer: 1024 * 1024 * 8, windowsHide: true },
      (error, stdout, stderr) => {
        if (stdout.length > 0) {
          outputChannel.append(stdout);
        }

        if (stderr.length > 0) {
          outputChannel.append(stderr);
        }

        if (error !== null) {
          outputChannel.show(true);
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
