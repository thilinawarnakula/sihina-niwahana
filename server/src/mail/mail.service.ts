/* Email the search summary. SMTP credentials from env only (never in code):
 * SMTP_USER / SMTP_PASS (Gmail App Password), optional SMTP_HOST / SMTP_PORT.
 * When ALLOWED_EMAILS is set, mail may only be SENT TO those addresses too
 * (anti-spam guard). */

import {
  BadRequestException, ForbiddenException, Injectable,
  ServiceUnavailableException,
} from "@nestjs/common";
import * as nodemailer from "nodemailer";

@Injectable()
export class MailService {
  get configured() {
    return !!(process.env.SMTP_USER && process.env.SMTP_PASS);
  }

  async send(to: string, subject: string, text: string, html?: string) {
    if (!this.configured)
      throw new ServiceUnavailableException(
        "Email is not configured. Set SMTP_USER and SMTP_PASS " +
        "(for Gmail use an App Password).");
    if (!to.includes("@"))
      throw new BadRequestException("Enter a valid email address");

    const allowed = (process.env.ALLOWED_EMAILS || "")
      .split(",").map((e) => e.trim().toLowerCase()).filter(Boolean);
    if (allowed.length && !allowed.includes(to.toLowerCase()))
      throw new ForbiddenException(
        "Recipient not in ALLOWED_EMAILS (anti-spam guard)");

    const transport = nodemailer.createTransport({
      host: process.env.SMTP_HOST || "smtp.gmail.com",
      port: parseInt(process.env.SMTP_PORT || "587", 10),
      secure: false,
      auth: { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS },
    });
    await transport.sendMail({
      from: process.env.SMTP_USER, to,
      subject: subject.slice(0, 200),
      text: text.slice(0, 100_000),
      html: html ? html.slice(0, 500_000) : undefined,
    });
    return { ok: true, sent: to };
  }
}
