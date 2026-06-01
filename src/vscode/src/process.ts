import * as cp from "node:child_process";
import type { CommandResult } from "./types";

export function runCommand(
  command: string,
  args: string[],
  cwd: string | undefined,
  timeout: number,
): Promise<CommandResult> {
  return new Promise((resolve) => {
    cp.execFile(
      command,
      args,
      {
        cwd,
        maxBuffer: 1024 * 1024 * 4,
        timeout,
        windowsHide: true,
      },
      (error, stdout, stderr) => {
        if (error !== null) {
          resolve({
            ok: false,
            stdout,
            stderr,
            error: [error.message, stderr.trim()].filter((part) => part.length > 0).join("\n"),
          });
          return;
        }

        resolve({
          ok: true,
          stdout,
          stderr,
        });
      },
    );
  });
}
