import {
  BadRequestException, Body, Controller, Get, Post, UseGuards,
} from "@nestjs/common";
import { FirebaseGuard } from "./auth/firebase.guard";
import { MailService } from "./mail/mail.service";
import { SearchService } from "./search/search.service";
import { Profile } from "./search/engine";

const VALID_TYPES = new Set(["land", "house", "apartment"]);

function validateProfile(data: any): Profile {
  const types = (data?.propertyTypes || []).filter((t: string) => VALID_TYPES.has(t));
  const purpose = data?.purpose;
  const areas = (data?.areas || [])
    .map((a: string) => String(a).trim()).filter(Boolean).slice(0, 8);
  if (!types.length || !["buy", "rent"].includes(purpose) || !areas.length)
    throw new BadRequestException(
      "Property type, purpose and at least one area are required");
  const num = (v: any) => {
    const n = parseFloat(v);
    return Number.isFinite(n) ? Math.round(n) : null;
  };
  return {
    propertyTypes: types, purpose, areas,
    budgetLKR: { min: num(data?.budgetLKR?.min), max: num(data?.budgetLKR?.max) },
    size: { bedrooms: num(data?.size?.bedrooms), perches: num(data?.size?.perches) },
    mustHaves: (data?.mustHaves || []).map((s: string) => String(s).trim())
      .filter(Boolean).slice(0, 10),
    dealBreakers: (data?.dealBreakers || []).map((s: string) => String(s).trim())
      .filter(Boolean).slice(0, 10),
  };
}

@Controller("api")
export class AppController {
  constructor(
    private readonly search: SearchService,
    private readonly mail: MailService,
  ) {}

  @Get("config")
  config() {
    return {
      loginMode: process.env.FIREBASE_API_KEY ? "firebase" : "none",
      emailConfigured: this.mail.configured,
    };
  }

  @Post("search")
  @UseGuards(FirebaseGuard)
  async doSearch(@Body() body: any) {
    return this.search.run(validateProfile(body));
  }

  @Post("mail")
  @UseGuards(FirebaseGuard)
  async doMail(@Body() body: any) {
    return this.mail.send(
      String(body?.to || "").trim(),
      String(body?.subject || "Property search results"),
      String(body?.text || ""),
      body?.html ? String(body.html) : undefined,
    );
  }
}
