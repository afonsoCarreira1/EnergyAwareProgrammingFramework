package com.tool;

import org.eclipse.lsp4j.services.LanguageClient;
import org.eclipse.lsp4j.PublishDiagnosticsParams;
import org.eclipse.lsp4j.jsonrpc.services.JsonNotification;

import java.util.Map;

public interface CustomLanguageClient extends LanguageClient {
    @JsonNotification("custom/updateSliders")
    void updateSliders(Map<String, Object> params);

    @JsonNotification("custom/updateEnergy")
    void updateEnergy(Map<String, Object> params);

    void publishDiagnostics(PublishDiagnosticsParams diagnostics);
}
