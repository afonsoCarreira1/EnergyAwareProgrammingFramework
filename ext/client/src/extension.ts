import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as fsp from 'fs/promises';
import { LanguageClient, LanguageClientOptions, ServerOptions } from 'vscode-languageclient/node';

let sliderPanel: vscode.WebviewPanel | undefined;
let client: LanguageClient;

async function installCustomLibs(context: vscode.ExtensionContext) {
    const sourceLibDir = context.asAbsolutePath(path.join('server', 'custom_progs'));
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

    console.log('Installing custom libs...');
    console.log('Source lib dir:', sourceLibDir);
    console.log('Workspace folder:', workspaceFolder);

    if (!workspaceFolder) {
        console.warn('No workspace folder found.');
        return;
    }

    const destLibDir = path.join(workspaceFolder, 'lib');

    try {
        await fsp.mkdir(destLibDir, { recursive: true });
        const files = await fsp.readdir(sourceLibDir);

        console.log('Files in source lib dir:', files);

        for (const file of files) {
            const sourcePath = path.join(sourceLibDir, file);
            const destPath = path.join(destLibDir, file);

            try {
                const stat = await fsp.stat(sourcePath);
                if (stat.isFile()) {
                    console.log(`Copying file: ${file}`);
                    await fsp.copyFile(sourcePath, destPath);
                } else if (stat.isDirectory()) {
                    console.log(`Skipping directory: ${file}`);
                } else {
                    console.log(`Skipping non-file/non-dir: ${file}`);
                }
            } catch (err) {
                console.warn(`Skipping ${file}: ${err}`);
            }
        }
    } catch (error) {
        console.error(`Failed to copy files to workspace/lib: ${error}`);
    }
}

export async function activate(context: vscode.ExtensionContext) {
    console.log('Activating extension...');
    console.log('Extension path:', context.extensionPath);

    const jarDir = context.asAbsolutePath('server');
    console.log('Server folder absolute path:', jarDir);

    const mainJar = path.join(jarDir, 'energy_prediction-1.0-SNAPSHOT-jar-with-dependencies.jar');
    console.log('JAR path:', mainJar);
    console.log('Does JAR exist?', fs.existsSync(mainJar));

    const serverOptions: ServerOptions = {
        command: 'java',
        args: ['-cp', mainJar, 'com.tool.App']
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'java' }]
    };

    client = new LanguageClient('javaLspServer', 'Java LSP Server', serverOptions, clientOptions);

    try {
        await client.start();
        console.log('Language client started successfully.');
    } catch (err) {
        console.error('LanguageClient failed to start:', err);
    }

    await installCustomLibs(context);

    client.onNotification('custom/updateSliders', (params) => {
        console.log('Received updateSliders:', params);
        if (sliderPanel) {
            sliderPanel.webview.postMessage({ type: 'updateSliders', ...params });
        }
    });

    client.onNotification('custom/updateEnergy', (params) => {
        console.log('Received updateEnergy:', params);
        if (sliderPanel) {
            sliderPanel.webview.postMessage({ type: 'updateEnergy', ...params });
        }
    });

    const disposable = vscode.commands.registerCommand('javaLspExtension.openEnergyExtension', async () => {
        sliderPanel = vscode.window.createWebviewPanel(
            'energyExtension',
            'Energy Extension',
            vscode.ViewColumn.Beside,
            { enableScripts: true }
        );

        const htmlPath = context.asAbsolutePath('media/sliders.html');
        console.log('Loading webview HTML from:', htmlPath);

        try {
            const buffer = await fsp.readFile(htmlPath);
            sliderPanel.webview.html = buffer.toString();
        } catch (err) {
            console.error('Failed to load webview HTML:', err);
        }

        sliderPanel.webview.onDidReceiveMessage(message => {
            console.log('Webview message:', message);
            switch (message.type) {
                case 'sliderChange':
                    client.sendNotification('custom/sliderChanged', { id: message.id, value: message.value });
                    break;
                case 'calculateEnergy':
                    client.sendNotification('custom/calculateEnergy');
                    break;
                default:
                    console.warn('Unknown message type:', message.type);
            }
        });

        sliderPanel.onDidDispose(() => sliderPanel = undefined);
    });

    context.subscriptions.push(disposable);
}

export function deactivate(): Thenable<void> | undefined {
    return client?.stop();
}
