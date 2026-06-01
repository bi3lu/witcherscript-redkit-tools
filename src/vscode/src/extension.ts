import * as vscode from "vscode";
import {
  DOCTOR_SETUP_COMMAND,
  REDKIT_INIT_COMMAND,
  REDKIT_LAUNCH_GAME_COMMAND,
  REDKIT_RECOMPILE_COMMAND,
  REFRESH_INDEX_COMMAND,
  RESTART_SERVER_COMMAND,
  SHOW_OUTPUT_COMMAND,
} from "./constants";
import { LanguageServerController } from "./languageServer";
import { initializeRedkitConfig, launchGame, recompileRedkitScripts } from "./redkitCommands";
import { doctorSetup } from "./setupDoctor";
import { WitcherScriptStatusBar } from "./statusBar";

let languageServer: LanguageServerController | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const outputChannel = vscode.window.createOutputChannel("WitcherScript");
  context.subscriptions.push(outputChannel);

  const statusBar = new WitcherScriptStatusBar(context);
  languageServer = new LanguageServerController(context, outputChannel, statusBar);
  const initializeConfig = async (): Promise<void> => {
    await initializeRedkitConfig(context, outputChannel, async () => {
      await languageServer?.refreshIndex();
    });
  };

  context.subscriptions.push(
    vscode.commands.registerCommand(SHOW_OUTPUT_COMMAND, () => {
      outputChannel.show(true);
    }),
    vscode.commands.registerCommand(DOCTOR_SETUP_COMMAND, async () => {
      await doctorSetup(context, outputChannel, requiredLanguageServer(), initializeConfig);
    }),
    vscode.commands.registerCommand(REFRESH_INDEX_COMMAND, async () => {
      await requiredLanguageServer().refreshIndex();
    }),
    vscode.commands.registerCommand(REDKIT_INIT_COMMAND, initializeConfig),
    vscode.commands.registerCommand(REDKIT_RECOMPILE_COMMAND, async () => {
      await recompileRedkitScripts(context, outputChannel);
    }),
    vscode.commands.registerCommand(REDKIT_LAUNCH_GAME_COMMAND, async () => {
      await launchGame(context, outputChannel);
    }),
    vscode.commands.registerCommand(RESTART_SERVER_COMMAND, async () => {
      await requiredLanguageServer().restart();
    }),
  );

  await languageServer.start();
}

export async function deactivate(): Promise<void> {
  await languageServer?.stop();
  languageServer = undefined;
}

function requiredLanguageServer(): LanguageServerController {
  if (languageServer === undefined) {
    throw new Error("WitcherScript language server controller is not initialized.");
  }

  return languageServer;
}
