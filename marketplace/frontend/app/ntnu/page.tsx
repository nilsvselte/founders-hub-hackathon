import type { Metadata } from "next";
import StudentRooms from "./student-rooms";

export const metadata: Metadata = {
  title: "NTNU · Student rooms · standbyroom",
  description: "Find a group room for your next study session with standbyroom's NTNU assistant.",
};

export default function NTNUPage() {
  return <StudentRooms />;
}
