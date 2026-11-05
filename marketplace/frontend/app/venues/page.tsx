import type { Metadata } from "next";
import VenueDirectory from "./venue-directory";

export const metadata: Metadata = {
  title: "standbyroom · Venues",
  description: "Browse meeting rooms, coworking spaces, hotels and event venues in Trondheim and Stjørdal.",
};

export default function VenuesPage() {
  return <VenueDirectory />;
}
