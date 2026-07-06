/* Search orchestration.
 *
 * Scaling upgrade over the Python/browser engines: tasks run in PARALLEL
 * across the four sites but strictly SEQUENTIAL (with a politeness delay)
 * within each site — same courtesy per host, ~4x less wall-clock time.
 * The fetch layer adds a shared in-memory 15-min cache, so every user
 * benefits from any user's recent fetches. */

import { Injectable, Logger } from "@nestjs/common";
import { fetchPage, FetchError } from "../http/fetch.util";
import {
  buildTasks, dedupe, manualLinks, rank, Listing, Profile, SearchTask,
} from "./engine";

const DELAY_MS = 1500;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

interface Coverage {
  [site: string]: { searched: string[]; count: number; errors: string[] };
}

@Injectable()
export class SearchService {
  private readonly log = new Logger(SearchService.name);

  async run(profile: Profile) {
    const { tasks, errors } = buildTasks(profile);
    const coverage: Coverage = {};
    const cov = (name: string) =>
      (coverage[name] ??= { searched: [], count: 0, errors: [] });
    for (const e of errors) cov("area lookup").errors.push(e);

    // group by site; parallel across groups, sequential + delayed within
    const groups = new Map<string, SearchTask[]>();
    for (const t of tasks)
      groups.set(t.name, [...(groups.get(t.name) || []), t]);

    const all: Listing[] = [];
    await Promise.all(
      [...groups.values()].map((group) => this.runGroup(group, cov, all)),
    );

    cov("patpat.lk").errors.push(
      "patpat: not searched (robots.txt disallows all crawling)");
    cov("CeylonProperty.lk").errors.push(
      "ceylonproperty: not searched (robots.txt disallows its search pages)");
    cov("Facebook Marketplace").errors.push(
      "facebook: not searched (no public API; scraping violates ToS)");

    return {
      savedAt: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
      profile,
      listings: rank(dedupe(all), profile),
      coverage,
      manualLinks: manualLinks(profile),
    };
  }

  private async runGroup(
    group: SearchTask[],
    cov: (name: string) => Coverage[string],
    all: Listing[],
  ) {
    for (const t of group) {
      let body: string | null = null;
      let cached = false;
      let used = t.url;
      try {
        ({ body, cached } = await fetchPage(t.url));
      } catch (e) {
        const canFallback = t.fallbackUrl &&
          (!(e instanceof FetchError) || e.status === 404);
        if (canFallback) {
          try {
            ({ body, cached } = await fetchPage((used = t.fallbackUrl!)));
          } catch (e2: any) {
            cov(t.name).errors.push(`${t.source}: ${e2.message}`);
          }
        } else {
          cov(t.name).errors.push(`${t.source}: ${(e as Error).message}`);
        }
      }
      if (body != null) {
        try {
          const listings = t.parse(body);
          cov(t.name).searched.push(used);
          cov(t.name).count += listings.length;
          all.push(...listings);
        } catch (e: any) {
          cov(t.name).errors.push(`${t.source}: parse failed: ${e.message}`);
        }
      }
      if (!cached) await sleep(DELAY_MS); // politeness gap per host
    }
    this.log.log(`${group[0].name}: done (${group.length} page(s))`);
  }
}
