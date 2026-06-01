import * as path from "node:path";
import * as vscode from "vscode";
import { State } from "vscode-languageclient/node";
import { CONFIG_SECTION } from "./constants";
import { languageServerCommand, redkitCommand } from "./configuration";
import type { LanguageServerController } from "./languageServer";
import {
  currentWorkspaceFolder,
  expandPath,
  fileExists,
  parseTomlString,
  parseTomlStringArray,
  pathExists,
  workspaceConfigUri,
} from "./paths";
import { runCommand } from "./process";

export async function doctorSetup(
  context: vscode.ExtensionContext,
  outputChannel: vscode.OutputChannel,
  languageServer: LanguageServerController,
  initializeConfig: () => Promise<void>,
): Promise<void> {
  const workspaceFolder = currentWorkspaceFolder();
  const checks: DoctorCheck[] = [];

  checks.push(workspaceCheck(workspaceFolder));
  checks.push(await configCheck(workspaceFolder));
  checks.push(await toolCheck("uv", "uv", ["--version"]));
  checks.push(await toolCheck("dotnet", "dotnet", ["--version"]));
  checks.push(await languageServerEnvironmentCheck(context, workspaceFolder));
  checks.push(languageServerStatusCheck(languageServer));
  checks.push(await redkitCliCheck(context, workspaceFolder));
  checks.push(...(await configPathChecks(workspaceFolder)));
  checks.push(recompileSettingCheck(context, workspaceFolder));

  const report = formatDoctorReport(checks, workspaceFolder);
  outputChannel.appendLine(report);
  outputChannel.show(true);

  const errors = checks.filter((check) => check.status === "error").length;
  const warnings = checks.filter((check) => check.status === "warning").length;
  const action = await showDoctorSummary(errors, warnings);

  if (action === "Initialize Config") {
    await initializeConfig();
  } else if (action === "Open Settings") {
    await vscode.commands.executeCommand(
      "workbench.action.openSettings",
      "@ext:witcherscript.witcherscript-redkit-tools",
    );
  } else if (action === "Open Report") {
    outputChannel.show(true);
  }
}

function workspaceCheck(workspaceFolder: vscode.WorkspaceFolder | undefined): DoctorCheck {
  if (workspaceFolder === undefined) {
    return {
      name: "Workspace",
      status: "error",
      message: "No workspace folder is open.",
      detail: "Open your REDkit mod workspace before running setup diagnostics.",
    };
  }

  return {
    name: "Workspace",
    status: "ok",
    message: workspaceFolder.uri.fsPath,
  };
}

async function configCheck(
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): Promise<DoctorCheck> {
  if (workspaceFolder === undefined) {
    return {
      name: "witcherscript.toml",
      status: "warning",
      message: "Skipped because no workspace folder is open.",
    };
  }

  const configPath = workspaceConfigUri(workspaceFolder);

  if (await fileExists(configPath)) {
    return {
      name: "witcherscript.toml",
      status: "ok",
      message: "Project configuration exists.",
      detail: configPath.fsPath,
    };
  }

  return {
    name: "witcherscript.toml",
    status: "error",
    message: "Project configuration is missing.",
    detail: "Run WitcherScript: Initialize REDkit Config.",
  };
}

async function toolCheck(name: string, command: string, args: string[]): Promise<DoctorCheck> {
  const result = await runCommand(command, args, undefined, 5000);

  if (result.ok) {
    return {
      name,
      status: "ok",
      message: result.stdout.trim() || `${command} is available.`,
    };
  }

  return {
    name,
    status: "error",
    message: `${command} is not available or failed to run.`,
    detail: result.error,
  };
}

async function languageServerEnvironmentCheck(
  context: vscode.ExtensionContext,
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): Promise<DoctorCheck> {
  const serverCommand = languageServerCommand(context, workspaceFolder);

  if (path.basename(serverCommand.command).toLowerCase().startsWith("uv")) {
    const result = await runCommand(
      serverCommand.command,
      ["run", "witcherscript", "version"],
      serverCommand.cwd,
      15000,
    );

    if (result.ok) {
      return {
        name: "Language server environment",
        status: "ok",
        message: result.stdout.trim() || "Bundled Python environment is runnable.",
        detail: `cwd: ${serverCommand.cwd}`,
      };
    }

    return {
      name: "Language server environment",
      status: "error",
      message: "Bundled Python environment failed to run.",
      detail: `${serverCommand.command} run witcherscript version\n${result.error}`,
    };
  }

  return {
    name: "Language server environment",
    status: "warning",
    message: "Custom language server command is configured.",
    detail: `${serverCommand.command} ${serverCommand.args.join(" ")}`,
  };
}

function languageServerStatusCheck(languageServer: LanguageServerController): DoctorCheck {
  if (languageServer.state === State.Running) {
    return {
      name: "Language server status",
      status: "ok",
      message: "Language server is running.",
    };
  }

  return {
    name: "Language server status",
    status: "warning",
    message: "Language server is not currently running.",
    detail: "Run WitcherScript: Restart Language Server after fixing setup issues.",
  };
}

async function redkitCliCheck(
  context: vscode.ExtensionContext,
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): Promise<DoctorCheck> {
  if (workspaceFolder === undefined) {
    return {
      name: "REDkit CLI",
      status: "warning",
      message: "Skipped because no workspace folder is open.",
    };
  }

  const { command, args } = redkitCommand(context, workspaceFolder);
  const result = await runCommand(command, [...args, "version"], workspaceFolder.uri.fsPath, 20000);

  if (result.ok) {
    return {
      name: "REDkit CLI",
      status: "ok",
      message: result.stdout.trim() || "REDkit CLI is runnable.",
    };
  }

  return {
    name: "REDkit CLI",
    status: "error",
    message: "REDkit CLI failed to run.",
    detail: `${command} ${[...args, "version"].join(" ")}\n${result.error}`,
  };
}

async function configPathChecks(
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): Promise<DoctorCheck[]> {
  if (workspaceFolder === undefined) {
    return [];
  }

  const configPath = workspaceConfigUri(workspaceFolder);

  if (!(await fileExists(configPath))) {
    return [];
  }

  const text = Buffer.from(await vscode.workspace.fs.readFile(configPath)).toString("utf8");
  const checks: DoctorCheck[] = [];
  checks.push(configuredPathCheck("Witcher 3 path", text, "game_directory", workspaceFolder));
  checks.push(configuredPathCheck("REDkit path", text, "redkit_directory", workspaceFolder));
  checks.push(configuredPathCheck("REDkit project path", text, "project_directory", workspaceFolder));
  checks.push(configuredRootsCheck("Script roots", text, "source_roots"));
  checks.push(configuredRootsCheck("Vanilla script roots", text, "vanilla_roots"));
  return checks;
}

function configuredPathCheck(
  name: string,
  configText: string,
  key: string,
  workspaceFolder: vscode.WorkspaceFolder,
): DoctorCheck {
  const configuredPath = parseTomlString(configText, key);

  if (configuredPath === undefined || configuredPath.trim().length === 0) {
    return {
      name,
      status: "warning",
      message: `${key} is not configured.`,
    };
  }

  const expandedPath = path.isAbsolute(configuredPath)
    ? configuredPath
    : path.join(workspaceFolder.uri.fsPath, configuredPath);

  if (pathExists(expandedPath)) {
    return {
      name,
      status: "ok",
      message: expandedPath,
    };
  }

  return {
    name,
    status: "error",
    message: `${key} does not exist.`,
    detail: expandedPath,
  };
}

function configuredRootsCheck(name: string, configText: string, key: string): DoctorCheck {
  const roots = parseTomlStringArray(configText, key);

  if (roots.length === 0) {
    return {
      name,
      status: "warning",
      message: `${key} is empty or not configured.`,
    };
  }

  return {
    name,
    status: "ok",
    message: `${roots.length} configured root(s).`,
    detail: roots.join(", "),
  };
}

function recompileSettingCheck(
  context: vscode.ExtensionContext,
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): DoctorCheck {
  const config = vscode.workspace.getConfiguration(CONFIG_SECTION);
  const executable = expandPath(
    config.get<string>("redkit.recompile.executable", ""),
    context,
    workspaceFolder,
  ).trim();

  if (executable.length === 0) {
    return {
      name: "Recompile executable",
      status: "warning",
      message: "witcherscript.redkit.recompile.executable is not configured.",
    };
  }

  if (pathExists(executable)) {
    return {
      name: "Recompile executable",
      status: "ok",
      message: executable,
    };
  }

  return {
    name: "Recompile executable",
    status: "error",
    message: "Configured recompile executable does not exist.",
    detail: executable,
  };
}

function formatDoctorReport(
  checks: DoctorCheck[],
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): string {
  const lines = [
    "",
    "WitcherScript Setup Doctor",
    `Workspace: ${workspaceFolder?.uri.fsPath ?? "<none>"}`,
    `Generated: ${new Date().toISOString()}`,
    "",
  ];

  for (const check of checks) {
    const detail = check.detail === undefined ? "" : `\n    ${check.detail}`;
    lines.push(`[${check.status.toUpperCase()}] ${check.name}: ${check.message}${detail}`);
  }

  return lines.join("\n");
}

async function showDoctorSummary(errors: number, warnings: number): Promise<string | undefined> {
  if (errors > 0) {
    return vscode.window.showErrorMessage(
      `WitcherScript setup has ${errors} error(s) and ${warnings} warning(s).`,
      "Open Report",
      "Initialize Config",
      "Open Settings",
    );
  }

  if (warnings > 0) {
    return vscode.window.showWarningMessage(
      `WitcherScript setup has ${warnings} warning(s).`,
      "Open Report",
      "Initialize Config",
      "Open Settings",
    );
  }

  return vscode.window.showInformationMessage(
    "WitcherScript setup looks good.",
    "Open Report",
  );
}

interface DoctorCheck {
  name: string;
  status: DoctorStatus;
  message: string;
  detail?: string;
}

type DoctorStatus = "error" | "ok" | "warning";
