import { Module } from "@nestjs/common";
import { AppController } from "./app.controller";
import { SearchService } from "./search/search.service";
import { MailService } from "./mail/mail.service";
import { FirebaseGuard } from "./auth/firebase.guard";

@Module({
  controllers: [AppController],
  providers: [SearchService, MailService, FirebaseGuard],
})
export class AppModule {}
