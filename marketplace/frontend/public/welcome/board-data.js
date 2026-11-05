// Fake data for the hero board. Times are minutes after midnight.
window.BOARD_DATA = {
  now: 15 * 60 + 20,
  defaults: { from: '15:15', to: '16:30', duration: 45, people: 4, equip: ['screen', 'whiteboard'], budget: 300, zone: 'quiet', flex: 15 },
  rooms: [
    { id: 'nidelva', name: 'Nidelva', seats: 8, equip: ['screen', 'video'], zone: 'open', list: 420, price: 260, from: '16:30', to: '17:30' },
    { id: 'booth2', name: 'Phone booth 2', seats: 1, equip: ['video'], zone: 'quiet', list: 90, price: 60, from: '15:20', to: '16:00' },
    { id: 'solsiden', name: 'Solsiden', seats: 4, equip: ['whiteboard'], zone: 'cafe', list: 300, price: 190, from: '15:00', to: '15:45' },
    { id: 'munkholmen', name: 'Munkholmen', seats: 6, equip: ['screen', 'whiteboard'], zone: 'quiet', list: 380, price: 240, from: '15:50', to: '16:50' },
    { id: 'ravnkloa', name: 'Ravnkloa', seats: 12, equip: ['screen', 'whiteboard', 'video'], zone: 'open', list: 650, price: 420, from: '15:30', to: '17:00' },
    { id: 'kristiansten', name: 'Kristiansten', seats: 3, equip: ['screen'], zone: 'quiet', list: 240, price: 150, from: '14:00', to: '15:10' }
  ],
  // Freed by staff pressing "Release room". 
  released: { id: 'bakklandet', name: 'Bakklandet', seats: 6, equip: ['screen', 'whiteboard', 'video'], zone: 'quiet', list: 320, price: 180, from: '15:25', to: '16:30' }
};
