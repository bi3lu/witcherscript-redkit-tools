import * as vscode from "vscode";
import { SHOW_OUTPUT_COMMAND } from "./constants";

export class WitcherScriptStatusBar {
  private readonly item: vscode.StatusBarItem;

  public constructor(context: vscode.ExtensionContext) {
    this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    this.item.command = SHOW_OUTPUT_COMMAND;
    this.item.tooltip = "WitcherScript Language Server";
    context.subscriptions.push(this.item);
    this.update("stopped");
  }

  public update(status: LspStatus, detail?: string): void {
    const label =
      detail === undefined ? STATUS_LABELS[status] : `${STATUS_LABELS[status]} (${detail})`;
    this.item.text = label;
    this.item.tooltip = `WitcherScript Language Server: ${status}`;
    this.item.show();
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

export type LspStatus = "error" | "indexing" | "running" | "starting" | "stopped" | "stopping";
