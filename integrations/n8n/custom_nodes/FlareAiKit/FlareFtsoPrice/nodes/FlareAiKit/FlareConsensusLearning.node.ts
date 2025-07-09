import {
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  IExecuteFunctions,
  NodeConnectionType,
} from "n8n-workflow";

export class FlareConsensusLearning implements INodeType {
  description: INodeTypeDescription = {
    displayName: "FLare Consensus Learning",
    name: "n8n-nodes-flareConsensusLearning",
    icon: "fa:search",
    group: ["transform"],
    version: 1,
    description:
      "Fetch Flare Consensus Learning data from Flare AI Kit FastAPI service",
    defaults: {
      name: "n8n-nodes-flareConsensusLearning",
    },
    inputs: ["main" as NodeConnectionType],
    outputs: ["main" as NodeConnectionType],
    properties: [
      {
        displayName: "Query",
        name: "query",
        type: "string",
        default: "",
        description:
          "Flare Consensus Learning query to find relevant documents",
      },
    ],
  };
  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const query = this.getNodeParameter("query", 0) as string;

    const response = await this.helpers.httpRequest({
      method: "POST",
      url: `http://host.docker.internal:8000/consensus-learning`,
      headers: { "Content-Type": "application/json" },
      body: { query },
      json: true,
    });

    return [[{ json: response }]];
  }
}
