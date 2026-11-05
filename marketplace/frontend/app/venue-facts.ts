// Public facts about pilot venues, collected from their websites on 5 November 2026.
// Keep "stated" facts to what a source says. Put anything read from a photo under "inferred".

export type VenueFacts = {
  id: string;
  name: string;
  tagline: string;
  address: string;
  photo: { src: string; alt: string };
  bookedToday: string;
  membership: string[];
  includes: string[];
  rooms: { roomId: string; stated: string; inferred?: string }[];
  notPublished: string[];
  sources: { label: string; url: string }[];
};

export const venueFacts: VenueFacts[] = [
  {
    id: "kowork",
    name: "Kowork",
    tagline: "Shared offices run by Koteng Eiendom in a building from 1841 in Trondheim city centre.",
    address: "Kjøpmannsgata 40, 7011 Trondheim",
    photo: { src: "/venues/kowork.webp", alt: "Kowork’s café and kitchen at Kjøpmannsgata 40" },
    bookedToday:
      "Only Kowork tenants can book the meeting room, through a tenant booking site. It’s included in their rent, so the room has no hourly price and outsiders can’t use it.",
    membership: [
      "Fixed desk or own room from NOK 3,650 a month",
      "Flex desk from NOK 3,000 a month or NOK 1,450 a week",
      "Prices exclude VAT",
    ],
    includes: ["Shared meeting room for 8–12", "Shared quiet room", "Wi-Fi and printer", "Coffee, tea and a kitchen"],
    rooms: [
      {
        roomId: "kowork-meeting-room",
        stated: "Shared meeting room for 8 to 12 people, tenants only, must be booked.",
        inferred: "Kowork’s photo shows one long table with about ten chairs and a wall-mounted screen with a soundbar.",
      },
      { roomId: "kowork-quiet-room", stated: "Shared quiet room for calls and conversations.", inferred: "Size not published. Capacity of 2 is our estimate." },
    ],
    notPublished: ["Room names", "Hourly prices", "Opening hours", "How often rooms sit empty"],
    sources: [
      { label: "koteng.no: Kowork", url: "https://koteng.no/kontorfellesskap-trondheim/" },
      { label: "koteng.no: Kjøpmannsgata 40", url: "https://koteng.no/eiendommer/kjopmannsgata-40/" },
    ],
  },
  {
    id: "brighten",
    name: "Brighten",
    tagline: "A members-only coworking space for self-employed people in Bakke Bydelshus, a 1914 parish house on Bakklandet.",
    address: "Bakke Bydelshus, Nordre Berggate 2, 7014 Trondheim",
    photo: { src: "/venues/brighten.webp", alt: "Brighten’s glass-walled meeting room on Bakklandet" },
    bookedToday:
      "Members book the meeting room and phone pod ahead or use them when they’re free. Both are included in the membership. There’s no drop-in, so the rooms aren’t available to anyone else.",
    membership: ["One membership at NOK 4,800 a month, excluding VAT", "Access 7 days a week", "Three months’ notice"],
    includes: ["Quiet zone with monitor workstations", "Meeting room and phone pod", "Coffee and a free monthly lunch"],
    rooms: [
      {
        roomId: "brighten-meeting-room",
        stated: "Meeting room for members, booked ahead or used when free.",
        inferred: "Brighten’s photos show one glass-walled room with a round table and four chairs, and no screen.",
      },
      { roomId: "brighten-phone-pod", stated: "Phone pod for calls and digital meetings. All calls happen here or in the meeting room." },
    ],
    notPublished: ["Room capacities", "Equipment", "Hourly prices", "Number of members"],
    sources: [
      { label: "brighten.no", url: "https://brighten.no" },
      { label: "Store norske leksikon: Bakklandet", url: "https://snl.no/Bakklandet" },
    ],
  },
];

export function factsForVenue(venueName: string) {
  return venueFacts.find((venue) => venue.name === venueName);
}
