import * as path from "node:path";
import * as vscode from "vscode";
import { CONFIG_SECTION } from "./constants";
import { currentWorkspaceFolder, expandPath, pathExists } from "./paths";
import type { CommandLine, LanguageServerCommand } from "./types";

export function effectiveWorkspaceFolder(
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

export function languageServerCommand(
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

export function redkitCommand(
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

  return {
    command,
    args: ["run", "--project", bundledRedkitCliProject(context), "--"],
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
