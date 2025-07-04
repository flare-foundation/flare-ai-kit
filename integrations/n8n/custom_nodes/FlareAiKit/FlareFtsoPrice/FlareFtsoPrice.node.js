"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.FlareFtsoPrice = void 0;
class FlareFtsoPrice {
  constructor() {
    this.description = {
      displayName: "FLare FTSO Price",
      name: "flareFtsoPrice",
      icon: "fa:cloud",
      group: ["transform"],
      version: 1,
      description: "Fetch FTSO price data from Flare AI Kit FastAPI service",
      defaults: {
        name: "Flare FTSO Price",
      },
      inputs: ["main"],
      outputs: ["main"],
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
  }
  async execute() {
    const symbol = this.getNodeParameter("symbol", 0);
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
module.exports = {
  FlareFtsoPrice,
};
