import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";

const disabled = process.env.LEFTHOOK === "0";
const hasGit = existsSync(".git");

if (disabled || !hasGit) {
  process.exit(0);
}

try {
  execFileSync("lefthook", ["install"], { stdio: "inherit" });
} catch {
  // Git hooks are a developer convenience; never block dependency installs.
}
