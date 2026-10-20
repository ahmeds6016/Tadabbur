// Each component owns its identity; fetch and component state stay local.
export function createRequestIdentity() {
  let generation = 0;
  const requests = new Map();
  return {
    reset() { generation += 1; requests.clear(); },
    start(resource, uid = null) {
      const sequence = (requests.get(resource) || 0) + 1;
      requests.set(resource, sequence);
      return { resource, uid, sequence, generation };
    },
    current(ticket, uid = null) {
      return ticket.generation === generation && ticket.uid === uid &&
        requests.get(ticket.resource) === ticket.sequence;
    },
  };
}
