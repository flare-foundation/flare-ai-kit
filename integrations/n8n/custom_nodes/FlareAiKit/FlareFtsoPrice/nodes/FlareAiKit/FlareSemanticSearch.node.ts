import {
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  IExecuteFunctions,
  NodeConnectionType,
} from "n8n-workflow";

export class FlareSemanticSearch implements INodeType {
  description: INodeTypeDescription = {
    displayName: "FLare Semantic Search",
    name: "n8n-nodes-flareSemanticSearch",
    icon: "fa:search",
    group: ["transform"],
    version: 1,
    description:
      "Fetch Flare Semantic Search data from Flare AI Kit FastAPI service",
    defaults: {
      name: "n8n-nodes-flareSemanticSearch",
    },
    inputs: ["main" as NodeConnectionType],
    outputs: ["main" as NodeConnectionType],
    properties: [
      {
        displayName: "Query",
        name: "query",
        type: "string",
        default: "",
        description: "Flare Semantic Search query to find relevant documents",
      },
    ],
  };
  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const query = this.getNodeParameter("query", 0) as string;

    const response = await this.helpers.httpRequest({
      method: "POST",
      url: `http://host.docker.internal:8000/semantic-search`,
      headers: { "Content-Type": "application/json" },
      body: { query },
      json: true,
    });

    return [[{ json: response }]];
  }
}
