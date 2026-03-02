export default function NotificationFeed() {
  // TODO: Display real-time pipeline events as a notification feed
  //       Subscribe to WebSocket at /ws/{application_id}
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-2">Live Updates</h2>
      <p className="text-sm text-gray-500">Connecting to event stream...</p>
    </div>
  )
}
