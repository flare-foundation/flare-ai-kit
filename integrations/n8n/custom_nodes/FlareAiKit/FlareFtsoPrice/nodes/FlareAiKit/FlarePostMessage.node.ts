import {
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  IExecuteFunctions,
  NodeConnectionType,
} from "n8n-workflow";

export class FlarePostMessage implements INodeType {
  description: INodeTypeDescription = {
    displayName: "FLare Post Message",
    name: "n8n-nodes-flarePostMessage",
    icon: "fa:search",
    group: ["transform"],
    version: 1,
    description: "Post a message to the Flare AI Kit FastAPI service",
    defaults: {
      name: "n8n-nodes-flarePostMessage",
    },
    inputs: ["main" as NodeConnectionType],
    outputs: ["main" as NodeConnectionType],
    properties: [
      {
        displayName: "Query",
        name: "query",
        type: "string",
        default: "",
        description: "Flare Post Message query to send to the service",
      },
    ],
  };
  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const query = this.getNodeParameter("query", 0) as string;

    const response = await this.helpers.httpRequest({
      method: "POST",
      url: `http://host.docker.internal:8000/post-message`,
      headers: { "Content-Type": "application/json" },
      body: { query },
      json: true,
    });

    return [[{ json: response }]];
  }
}
