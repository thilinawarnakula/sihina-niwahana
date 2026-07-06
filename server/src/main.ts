/* Sihina Niwahana — NestJS backend.
 *
 * Run:   npm run dev      (ts-node, port 3001; PORT env to change)
 * Build: npm run build && npm start
 *
 * In production it also serves the built React app from ../client/dist. */

import "reflect-metadata";
import { NestFactory } from "@nestjs/core";
import { NestExpressApplication } from "@nestjs/platform-express";
import { existsSync } from "fs";
import { join } from "path";
import { AppModule } from "./app.module";

async function bootstrap() {
  const app = await NestFactory.create<NestExpressApplication>(AppModule, {
    logger: ["log", "warn", "error"],
  });

  const clientDist = join(__dirname, "..", "..", "client", "dist");
  if (existsSync(clientDist)) {
    app.useStaticAssets(clientDist);
    // SPA fallback for non-API routes
    (app.getHttpAdapter().getInstance() as any).get(/^(?!\/api).*/,
      (_req: any, res: any) => res.sendFile(join(clientDist, "index.html")));
  }

  const port = parseInt(process.env.PORT || "3001", 10);
  await app.listen(port);
  const auth = process.env.FIREBASE_API_KEY
    ? "Firebase auth ON" : "auth OFF (set FIREBASE_API_KEY)";
  console.log(`Sihina Niwahana API: http://localhost:${port}  [${auth}]`);
}
bootstrap();
