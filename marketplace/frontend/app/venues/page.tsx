import type { Metadata } from "next";
import VenueDirectory from "./venue-directory";

export const metadata: Metadata = {
  title: "Roomline · Pilot venues",
  description: "Kowork and Brighten in Trondheim: their rooms, how they're booked today, and what Roomline opens up.",
};

export default function VenuesPage() {
  return <VenueDirectory />;
}
