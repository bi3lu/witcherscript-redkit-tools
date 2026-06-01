export interface CommandLine {
  command: string;
  args: string[];
}

export interface CommandResult {
  ok: boolean;
  stdout: string;
  stderr: string;
  error?: string;
}

export interface LanguageServerCommand extends CommandLine {
  cwd: string;
}
