import type { AgentName } from "./types";

export interface Quote {
  agent: AgentName;
  character: string; // who said it on the show
  text: string | null; // null = not pinned up yet
}

// The break-room quotes board: one short, well-known line per character from
// Parks and Recreation. Only lines we can quote word for word are filled in;
// add your favorites for Ben and Chris by replacing `null` with the quote.
export const QUOTES: Quote[] = [
  { agent: "boss", character: "Ron Swanson", text: "Never half-ass two things. Whole-ass one thing." },
  { agent: "inventory", character: "April Ludgate", text: "I don't want to do things. I want to not do things." },
  { agent: "accounting", character: "Ben Wyatt", text: null },
  { agent: "facilities", character: "Chris Traeger", text: null },
  {
    agent: "customer_service",
    character: "Leslie Knope",
    text: "I am big enough to admit that I am often inspired by myself.",
  },
];

export const SHOW = "Parks and Recreation";
