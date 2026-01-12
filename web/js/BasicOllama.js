
import { app } from "../../../scripts/app.js"
import { api } from "../../../scripts/api.js";

const TypeSlot = {
    Input: 1,
    Output: 2,
};

const TypeSlotEvent = {
    Connect: true,
    Disconnect: false,
};

const _ID = "BasicOllama";
const _PREFIX = "image";
const _TYPE = "IMAGE";

app.registerExtension({
	name: 'cozy_ex.' + _ID,
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
        // skip the node if it is not the one we want
        if (nodeData.name !== _ID) {
            return
        }

        // Add event listener for runtime connection errors
        api.addEventListener("basic_ollama_connection_error", (event) => {
            const nodeId = event.detail.node_id;
            const node = app.graph.getNodeById(nodeId);
            if (node) {
                 const errorColor = "#550000";
                 if (node.bgcolor !== errorColor) {
                      node._original_bgcolor = node.bgcolor;
                      node.bgcolor = errorColor;
                 }
                 node.setDirtyCanvas(true);
            }
        });

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = async function () {
            const me = onNodeCreated?.apply(this);
            // start with a new dynamic input
            this.addInput(_PREFIX, _TYPE);
	    // Ensure the new slot has proper appearance
            const slot = this.inputs[this.inputs.length - 1];
            if (slot) {
                slot.color_off = "#666";
            }
            
            // Populate models
            this.populateModels();

            return me;
        }

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function () {
            onConfigure?.apply(this, arguments);
            this.populateModels();
        };

        nodeType.prototype.populateModels = async function () {
            const widget = this.widgets?.find((w) => w.name === "ollama_model");
            if (!widget) return;

            const errorMsg = "Start Ollama and Refresh";
            const errorColor = "#550000"; // Dark red for error
            
            // Save original color if not already saved and we are currently in error state
            if (this.bgcolor !== errorColor && this.bgcolor !== undefined) {
                 this._original_bgcolor = this.bgcolor;
            }

            try {
                const response = await api.fetchApi('/basic_ollama/models');
                if (response.ok) {
                    const models = await response.json();
                    if (models && models.length > 0) {
                        widget.options.values = models;
                        
                        // Check if the returned list is actually the error message from Python
                        if (models.length === 1 && models[0] === errorMsg) {
                             this.bgcolor = errorColor;
                             widget.value = errorMsg;
                        } else {
                            // Success case: Restore color
                            if (this.bgcolor === errorColor) {
                                this.bgcolor = this._original_bgcolor;
                            }
                            
                            // If current value is invalid or the placeholder, update it
                            if (!models.includes(widget.value)) {
                                widget.value = models[0];
                            }
                        }
                    }
                }
            } catch (err) {
                console.error("Error fetching Ollama models:", err);
                widget.options.values = [errorMsg];
                widget.value = errorMsg;
                this.bgcolor = errorColor;
            }
            
            this.setDirtyCanvas(true);
        };

        const onConnectionsChange = nodeType.prototype.onConnectionsChange
        nodeType.prototype.onConnectionsChange = function (slotType, slot_idx, event, link_info, node_slot) {
            const me = onConnectionsChange?.apply(this, arguments);

            if (slotType === TypeSlot.Input) {
                if (link_info && event === TypeSlotEvent.Connect) {
                    // get the parent (left side node) from the link
                    const fromNode = this.graph._nodes.find(
                        (otherNode) => otherNode.id == link_info.origin_id
                    )

                    if (fromNode) {
                        // make sure there is a parent for the link
                        const parent_link = fromNode.outputs[link_info.origin_slot];
                        if (parent_link) {
                            node_slot.type = parent_link.type;
                            node_slot.name = `${_PREFIX}_`;
                        }
                    }
                } else if (event === TypeSlotEvent.Disconnect) {
                    this.removeInput(slot_idx);
                }

                // Track each slot name so we can index the uniques
                let idx = 0;
                let slot_tracker = {};
                for(const slot of this.inputs) {
                    if (slot.link === null) {
                        try {
                            this.removeInput(idx);
                        } catch {

                        }
                        continue;
                    }
                    idx += 1;
                    const name = slot.name.split('_')[0];

                    // Correctly increment the count in slot_tracker
                    let count = (slot_tracker[name] || 0) + 1;
                    slot_tracker[name] = count;

                    // Update the slot name with the count if greater than 1
                    slot.name = `${name}_${count}`;
                }

                // check that the last slot is a dynamic entry....
                let last = this.inputs[this.inputs.length - 1];
                if (last === undefined || (last.name != _PREFIX || last.type != _TYPE)) {
                    this.addInput(_PREFIX, _TYPE);
		            // Set the unconnected slot to appear gray
                    last = this.inputs[this.inputs.length - 1];
                    if (last) {
                        last.color_off = "#666";
                    }
                }

                // force the node to resize itself for the new/deleted connections
                this?.graph?.setDirtyCanvas(true);
                return me;
            }
        }
        return nodeType;
    },

})
