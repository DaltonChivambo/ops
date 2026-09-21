import { phaseFor, type ScrollRoom } from './page-first-scroll';

function room(overrides: Partial<ScrollRoom> = {}): ScrollRoom {
  return { toAnchor: 0, belowPage: 0, listOffset: 0, pageOffset: 0, ...overrides };
}

const DOWN = 120;
const UP = -120;

describe('phaseFor', () => {
  it('desce a página enquanto a âncora não assentar', () => {
    expect(phaseFor(DOWN, room({ toAnchor: 80, belowPage: 400 }))).toBe('page');
  });

  it('entrega à lista quando a âncora assentou', () => {
    expect(phaseFor(DOWN, room({ toAnchor: 0, belowPage: 400 }))).toBe('list');
  });

  it('entrega à lista a um sub-píxel do fim', () => {
    // O caso que fazia a tabela tremer: o `getBoundingClientRect` devolve
    // píxeis fraccionários e o scroll assenta em píxeis do ecrã, por isso este
    // valor oscilava à volta de 1 entre tiques consecutivos.
    expect(phaseFor(DOWN, room({ toAnchor: 1.4, belowPage: 400 }))).toBe('list');
  });

  it('entrega à lista quando a página já não tem para onde descer', () => {
    expect(phaseFor(DOWN, room({ toAnchor: 80, belowPage: 0 }))).toBe('list');
  });

  it('a subir, a lista corre primeiro', () => {
    expect(phaseFor(UP, room({ listOffset: 300, pageOffset: 200 }))).toBe('list');
  });

  it('a subir com a lista no início, sobe a página', () => {
    expect(phaseFor(UP, room({ listOffset: 0, pageOffset: 200 }))).toBe('page');
  });

  it('a subir com tudo no início, não há nada a fazer à página', () => {
    expect(phaseFor(UP, room({ listOffset: 0, pageOffset: 0 }))).toBe('list');
  });
});
