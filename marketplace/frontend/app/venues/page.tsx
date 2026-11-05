import type { Metadata } from "next";
import VenueDirectory from "./venue-directory";

export const metadata: Metadata = {
  title: "standbyroom · Pilot venues",
  description: "Kowork and Brighten in Trondheim: their rooms, how they're booked today, and what standbyroom opens up.",
};

export default function VenuesPage() {
  return <VenueDirectory />;
}
