import {
  IAuthenticateGeneric,
  ICredentialTestRequest,
  ICredentialType,
  INodeProperties,
} from "n8n-workflow";

export class FlarePostMessage implements ICredentialType {
  name = "flarePostMessage";
  displayName = "Flare Post Message API";
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
      url: "http://host.docker.internal:8000/post-message",
      body: {
        platform: "twitter",
        message: "test message",
      },
      json: true,
    },
  };
}
