import {
  IAuthenticateGeneric,
  ICredentialTestRequest,
  ICredentialType,
  INodeProperties,
} from "n8n-workflow";

export class FlareSemanticSearchApi implements ICredentialType {
  name = "flareSemanticSearchApi";
  displayName = "Flare Semantic Search API";
  documentationUrl = ""; // Optional
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
      description: "Your API key for Flare Semantic Search API",
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
      url: "http://host.docker.internal:8000/semantic-search",
      body: {
        query: "test",
      },
      json: true,
    },
  };
}
