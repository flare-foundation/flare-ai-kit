# Docker commands

Build the example. Note MUST BE EXECUTED FROM flare-ai-kit ROOT
```docker build --no-cache --progress=plain -t flare-ai-kit-web-chatbot -f examples/web-chatbot/Dockerfile .```

Run the container and start the servers
```docker run --rm -p 80:80 -it --env-file .env flare-ai-kit-web-chatbot```

Clear containers and images
```docker builder prune --all```

## Clear all docker images, build, and then run the container
```zsh
docker builder prune --all &&
docker build --no-cache --progress=plain -t flare-ai-kit-web-chatbot -f examples/web-chatbot/Dockerfile . > build.log 2>&1 &&
docker run --rm -p 80:80 -it --env-file .env flare-ai-kit-web-chatbot
```
