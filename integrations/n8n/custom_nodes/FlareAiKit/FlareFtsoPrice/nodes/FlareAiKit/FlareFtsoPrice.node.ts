import {
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  IExecuteFunctions,
  NodeConnectionType,
} from "n8n-workflow";

export class FlareFtsoPrice implements INodeType {
  description: INodeTypeDescription = {
    displayName: "FLare FTSO Price",
    name: "n8n-nodes-flareFtsoPrice",
    icon: "fa:cloud",
    group: ["transform"],
    version: 1,
    description: "Fetch FTSO price data from Flare AI Kit FastAPI service",
    defaults: {
      name: "n8n-nodes-flareFtsoPrice",
    },
    inputs: ["main" as NodeConnectionType],
    outputs: ["main" as NodeConnectionType],
    properties: [
      {
        displayName: "Asset Symbol",
        name: "symbol",
        type: "string",
        default: "FLR",
        description:
          "Symbol of the asset to fetch the price for (e.g., FLR, SGB)",
      },
    ],
  };
  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const symbol = this.getNodeParameter("symbol", 0) as string;

    const response = await this.helpers.httpRequest({
      method: "GET",
      url: `http://host.docker.internal:8000/ftso/price?symbol=${symbol}`,
      headers: {
        "Content-Type": "application/json",
      },
    });
    return [[{ json: response }]];
  }
}
