import { setupServer } from "msw/node";
import { locateQuoteHandler } from "./handlers";
import { emptyWorkbenchHandlers } from "./workbenchHandlers";

export const server = setupServer(locateQuoteHandler, ...emptyWorkbenchHandlers);
