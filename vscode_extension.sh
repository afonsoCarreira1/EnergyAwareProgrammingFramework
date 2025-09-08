#!/bin/bash

if [ "$1" == "install" ]; then
    cd ext/client
    npm run compile
    cd ..
    npm run package --allow-missing-license
    code --install-extension client/java-lsp-slider-extension-0.0.1.vsix
elif [ "$1" == "uninstall" ]; then
    code --uninstall-extension "afonso.java-lsp-slider-extension"
    cd .. rm -rf lib/
else
    echo "Usage: $0 {install|uninstall}"
    exit 1
fi
