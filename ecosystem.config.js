const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const PYTHON_VERSION = "3.10.8";

function collectCandidates(version) {
  const candidates = [];

  const explicitEnv = process.env.PYENV_PYTHON_3_10_8 || process.env.SCRAPLING_PYTHON_PATH;
  if (explicitEnv) {
    candidates.push(explicitEnv);
  }

  try {
    const pyenvRoot = execSync("pyenv root", { encoding: "utf8" }).trim();
    if (pyenvRoot) {
      candidates.push(buildPyenvPath(pyenvRoot, version));
    }
  } catch (error) {
    // Ignore errors when pyenv is not available in PATH.
  }

  const potentialRoots = [
    process.env.PYENV,
    process.env.PYENV_ROOT,
    process.env.HOME && path.join(process.env.HOME, ".pyenv"),
    process.env.USERPROFILE && path.join(process.env.USERPROFILE, ".pyenv", "pyenv-win"),
    process.env.USERPROFILE && path.join(process.env.USERPROFILE, ".pyenv"),
  ].filter(Boolean);

  potentialRoots.forEach((root) => {
    candidates.push(buildPyenvPath(root, version));
  });

  return candidates;
}

function buildPyenvPath(root, version) {
  const isWindows = process.platform === "win32";
  const execRelativePath = isWindows ? ["versions", version, "python.exe"] : ["versions", version, "bin", "python"];
  return path.join(root, ...execRelativePath);
}

function findPyenvPython(version) {
  const candidates = collectCandidates(version);

  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return null;
}

const pythonBinary = findPyenvPython(PYTHON_VERSION) || "python";

module.exports = {
  apps: [
    {
      name: "scrapling-api",
      script: pythonBinary,
      args: "-m uvicorn app.main:app --host 0.0.0.0 --port 5680",
      interpreter: "none",
      cwd: __dirname,
      autorestart: true,
    },
  ],
};
