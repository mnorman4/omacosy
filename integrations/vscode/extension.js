"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const vscode = require("vscode");

const CURRENT_DIR = path.join(os.homedir(), ".config", "omarchy", "current");
const CURRENT_THEME = path.join(CURRENT_DIR, "theme");

/** @param {vscode.ExtensionContext} context */
function activate(context) {
  const output = vscode.window.createOutputChannel("Omacosy Theme");
  context.subscriptions.push(output);

  const contributed = context.extension.packageJSON.contributes?.themes ?? [];
  const themes = new Map(contributed.flatMap((theme) => {
    const match = /^\.\/themes\/(.+)-color-theme\.json$/.exec(theme.path);
    return match ? [[match[1], theme.label]] : [];
  }));

  let timer;
  const scheduleSync = () => {
    clearTimeout(timer);
    timer = setTimeout(() => syncTheme(output, themes), 100);
  };

  try {
    const watcher = fs.watch(CURRENT_DIR, scheduleSync);
    watcher.on("error", (error) => output.appendLine(`watch failed: ${error.message}`));
    context.subscriptions.push({
      dispose() {
        clearTimeout(timer);
        watcher.close();
      },
    });
  } catch (error) {
    output.appendLine(`watch unavailable: ${error.message}`);
  }

  void syncTheme(output, themes);
}

/**
 * @param {vscode.OutputChannel} output
 * @param {Map<string, string>} themes
 */
async function syncTheme(output, themes) {
  let themeName;
  try {
    themeName = path.basename(await fs.promises.realpath(CURRENT_THEME));
  } catch (error) {
    output.appendLine(`current theme unavailable: ${error.message}`);
    return;
  }

  const desired = themes.get(themeName);
  if (!desired) {
    output.appendLine(`no contributed theme for ${themeName}; leaving VS Code unchanged`);
    return;
  }

  const configuration = vscode.workspace.getConfiguration("workbench");
  const inspected = configuration.inspect("colorTheme");
  if (!inspected) {
    output.appendLine("workbench.colorTheme is unavailable");
    return;
  }

  const workspaceOverride = inspected.workspaceFolderValue ?? inspected.workspaceValue;
  if (workspaceOverride !== undefined && workspaceOverride !== desired) {
    output.appendLine(`workspace theme override ${JSON.stringify(workspaceOverride)} preserved`);
    return;
  }

  if (inspected.globalValue === desired) {
    return;
  }

  try {
    await configuration.update("colorTheme", desired, vscode.ConfigurationTarget.Global);
    output.appendLine(`selected ${desired}`);
  } catch (error) {
    output.appendLine(`could not select ${desired}: ${error.message}`);
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
