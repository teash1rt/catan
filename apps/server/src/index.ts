import { defineServer } from "colyseus";

const port = Number.parseInt(process.env.PORT ?? "2567", 10);
const server = defineServer({ rooms: {} });

await server.listen(port);
