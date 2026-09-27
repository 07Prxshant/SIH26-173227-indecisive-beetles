import { createFileRoute } from "@tanstack/react-router";
import Dashboard from "@/components/dashboard/Dashboard";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "UrbanSense | Road Incident Overview" },
      {
        name: "description",
        content:
          "Explore an illustrative map of detected road incidents, confidence scores, and sighting details in Bengaluru.",
      },
      { property: "og:title", content: "UrbanSense | Road Incident Overview" },
      {
        property: "og:description",
        content:
          "Explore an illustrative map of detected road incidents, confidence scores, and sighting details in Bengaluru.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Dashboard,
});
