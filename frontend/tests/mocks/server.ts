import { setupServer } from "msw/node";
import { locateQuoteHandler } from "./handlers";

export const server = setupServer(locateQuoteHandler);
