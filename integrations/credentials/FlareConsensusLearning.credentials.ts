import {
  IAuthenticateGeneric,
  ICredentialTestRequest,
  ICredentialType,
  INodeProperties,
} from "n8n-workflow";

export class FlareConsensusLearning implements ICredentialType {
  name = "flareConsensusLearning";
  displayName = "Flare Consensus Learning API";
  documentationUrl = ""; // Optional: Add if you want to link docs
  properties: INodeProperties[] = [
    {
      displayName: "API Key",
      name: "apiKey",
      type: "string",
      default: "",
      required: true,
      typeOptions: {
        password: true,
      },
      description: "The API key to authenticate with the Flare API wrapper.",
    },
  ];

  authenticate: IAuthenticateGeneric = {
    type: "generic",
    properties: {
      headers: {
        Authorization: "=Bearer {{$credentials.apiKey}}",
      },
    },
  };

  test: ICredentialTestRequest = {
    request: {
      method: "POST",
      url: "http://host.docker.internal:8000/consensus-learning",
      body: {
        data: ["test input"],
      },
      json: true,
    },
  };
}
