import * as fs from "node:fs";
import * as path from "node:path";
import * as vscode from "vscode";

export function currentWorkspaceFolder(): vscode.WorkspaceFolder | undefined {
  const activeDocument = vscode.window.activeTextEditor?.document;

  if (activeDocument !== undefined) {
    const folder = vscode.workspace.getWorkspaceFolder(activeDocument.uri);

    if (folder !== undefined) {
      return folder;
    }
  }

  return vscode.workspace.workspaceFolders?.[0];
}

export function expandPath(
  value: string,
  context: vscode.ExtensionContext,
  workspaceFolder: vscode.WorkspaceFolder | undefined,
): string {
  return value
    .replaceAll("${extensionPath}", context.extensionPath)
    .replaceAll("${workspaceFolder}", workspaceFolder?.uri.fsPath ?? "");
}

export function pathExists(candidate: string): boolean {
  try {
    return fs.existsSync(candidate);
  } catch {
    return false;
  }
}

export async function fileExists(uri: vscode.Uri): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

export function workspaceConfigUri(workspaceFolder: vscode.WorkspaceFolder): vscode.Uri {
  return vscode.Uri.file(path.join(workspaceFolder.uri.fsPath, "witcherscript.toml"));
}

export function parseTomlString(text: string, key: string): string | undefined {
  const escapedKey = escapeRegExp(key);
  const match = new RegExp(`^\\s*${escapedKey}\\s*=\\s*"([^"]*)"`, "m").exec(text);
  return match?.[1];
}

export function parseTomlStringArray(text: string, key: string): string[] {
  const escapedKey = escapeRegExp(key);
  const match = new RegExp(`^\\s*${escapedKey}\\s*=\\s*\\[([\\s\\S]*?)\\]`, "m").exec(text);

  if (match === null) {
    return [];
  }

  return [...match[1].matchAll(/"([^"]+)"/g)].map((item) => item[1]);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
