import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "BasicOllama.HideAutoRefresh",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // Only target your specific node
        if (nodeData.name === "BasicOllama") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            
            nodeType.prototype.onNodeCreated = function () {
                if (onNodeCreated) {
                    onNodeCreated.apply(this, arguments);
                }

                // Intercept ANY widget ComfyUI tries to add to this node
                const origAddWidget = this.addWidget;
                this.addWidget = function (type, name, value, callback, options) {
                    // Let the widget be created so ComfyUI's backend doesn't crash
                    const w = origAddWidget.apply(this, arguments);
                    
                    // If the widget is the annoying auto-refresh toggle, hide it instantly
                    if (name && typeof name === "string" && name.toLowerCase().includes("auto-refresh")) {
                        w.type = "hidden";           // Tell LiteGraph not to draw it
                        w.computeSize = () => [0, -4]; // Force its height to 0 pixels
                    }
                    return w;
                };

                // Cleanup: just in case it was already added before interception
                if (this.widgets) {
                    for (let w of this.widgets) {
                        if (w.name && w.name.toLowerCase().includes("auto-refresh")) {
                            w.type = "hidden";
                            w.computeSize = () => [0, -4];
                        }
                    }
                }
            };
        }
    }
});