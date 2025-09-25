const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const PREFERRED_PYTHON_VERSIONS = ["3.10.8", "3.10"];
const FALLBACK_BINARIES = ["python3.10", "python3", "python"];

function collectCandidates(versionSpecs) {
  const normalizedVersionSpecs = Array.isArray(versionSpecs) ? versionSpecs : [versionSpecs];
  const candidates = [];

  const explicitEnv = process.env.PYENV_PYTHON_3_10_8 || process.env.SCRAPLING_PYTHON_PATH;
  if (explicitEnv) {
    candidates.push(explicitEnv);
  }

  const potentialRoots = new Set();

  try {
    const pyenvRoot = execSync("pyenv root", { encoding: "utf8" }).trim();
    if (pyenvRoot) {
      potentialRoots.add(pyenvRoot);
    }
  } catch (error) {
    // Ignore errors when pyenv is not available in PATH.
  }

  [
    process.env.PYENV,
    process.env.PYENV_ROOT,
    process.env.HOME && path.join(process.env.HOME, ".pyenv"),
    process.env.USERPROFILE && path.join(process.env.USERPROFILE, ".pyenv", "pyenv-win"),
    process.env.USERPROFILE && path.join(process.env.USERPROFILE, ".pyenv"),
  ]
    .filter(Boolean)
    .forEach((root) => potentialRoots.add(root));

  normalizedVersionSpecs.forEach((versionSpec) => {
    potentialRoots.forEach((root) => {
      buildPyenvPaths(root, versionSpec).forEach((resolvedPath) => {
        candidates.push(resolvedPath);
      });
    });
  });

  return candidates;
}

function buildPyenvPaths(root, versionSpec) {
  const isWindows = process.platform === "win32";
  const paths = [];
  const baseRelativePath = isWindows
    ? ["versions", versionSpec, "python.exe"]
    : ["versions", versionSpec, "bin", "python"];

  paths.push(path.join(root, ...baseRelativePath));

  const isPartialVersion = versionSpec.split(".").length < 3;
  if (!isPartialVersion) {
    return paths;
  }

  const versionsDir = path.join(root, "versions");

  try {
    const entries = fs.readdirSync(versionsDir, { withFileTypes: true });
    const matching = entries
      .filter((entry) => entry.isDirectory() && entry.name.startsWith(`${versionSpec}.`))
      .map((entry) => entry.name)
      .sort((a, b) => compareVersionStrings(b, a));

    matching.forEach((versionName) => {
      const execRelativePath = isWindows
        ? ["versions", versionName, "python.exe"]
        : ["versions", versionName, "bin", "python"];
      paths.push(path.join(root, ...execRelativePath));
    });
  } catch (error) {
    // Ignore missing versions directories or read errors.
  }

  return paths;
}

function compareVersionStrings(left, right) {
  const leftParts = left.split(".").map(Number);
  const rightParts = right.split(".").map(Number);
  const maxLength = Math.max(leftParts.length, rightParts.length);

  for (let index = 0; index < maxLength; index += 1) {
    const difference = (leftParts[index] || 0) - (rightParts[index] || 0);
    if (difference !== 0) {
      return difference;
    }
  }

  return 0;
}

function findPyenvPython(versionSpecs) {
  const candidates = collectCandidates(versionSpecs);

  for (const candidate of candidates) {
    if (candidate && fs.existsSync(candidate)) {
      return candidate;
    }
  }

  return null;
}

function commandExists(command) {
  const lookup = process.platform === "win32" ? `where ${command}` : `command -v ${command}`;

  try {
    execSync(lookup, { stdio: "ignore" });
    return true;
  } catch (error) {
    return false;
  }
}

function findPythonBinary(versionSpecs) {
  const pyenvBinary = findPyenvPython(versionSpecs);
  if (pyenvBinary) {
    return pyenvBinary;
  }

  for (const command of FALLBACK_BINARIES) {
    if (commandExists(command)) {
      return command;
    }
  }

  return "python";
}

const pythonBinary = findPythonBinary(PREFERRED_PYTHON_VERSIONS);

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
