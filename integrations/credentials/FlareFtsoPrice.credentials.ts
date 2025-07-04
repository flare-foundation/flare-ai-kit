import {
  IAuthenticateGeneric,
  ICredentialTestRequest,
  ICredentialType,
  INodeProperties,
} from "n8n-workflow";

export class FlareFtsoApi implements ICredentialType {
  name = "flareFtsoApi";
  displayName = "Flare FTSO API";
  documentationUrl = ""; // Optional, add a link to your API docs if available
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
      description: "Your API key for accessing the Flare FTSO API",
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
      method: "GET",
      url: "http://host.docker.internal:8000/ftso/price?asset=flare",
    },
  };
}
