import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ImageComparer from './ImageComparer.vue'

describe('ImageComparer', () => {
  it('renders before and after images with default labels', () => {
    const wrapper = mount(ImageComparer, {
      props: { beforeUrl: '/api/results/before.png', afterUrl: '/api/results/after.png' },
    })

    const imgs = wrapper.findAll('img')
    expect(imgs).toHaveLength(2)
    expect(imgs[0].attributes('src')).toBe('/api/results/after.png')
    expect(imgs[1].attributes('src')).toBe('/api/results/before.png')
    expect(wrapper.text()).toContain('Before')
    expect(wrapper.text()).toContain('After')
  })

  it('honours custom labels', () => {
    const wrapper = mount(ImageComparer, {
      props: {
        beforeUrl: '/a.png',
        afterUrl: '/b.png',
        beforeLabel: 'Original',
        afterLabel: 'Enhanced',
      },
    })

    expect(wrapper.text()).toContain('Original')
    expect(wrapper.text()).toContain('Enhanced')
  })

  it('updates the slider position on pointer drag', async () => {
    const wrapper = mount(ImageComparer, {
      props: { beforeUrl: '/a.png', afterUrl: '/b.png' },
    })

    const el = wrapper.find('.compare').element as HTMLElement
    vi.spyOn(el, 'getBoundingClientRect').mockReturnValue({
      left: 0,
      width: 200,
      top: 0,
      height: 100,
      right: 200,
      bottom: 100,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect)

    const handle = wrapper.find('.compare-handle').element as HTMLElement
    const move = wrapper.find('.compare').element as HTMLElement

    handle.dispatchEvent(
      new PointerEvent('pointerdown', { clientX: 150, pointerId: 1, bubbles: true }),
    )
    move.dispatchEvent(
      new PointerEvent('pointermove', { clientX: 100, pointerId: 1, bubbles: true }),
    )
    await wrapper.vm.$nextTick()

    const style = wrapper.find('.compare-handle').attributes('style') ?? ''
    expect(style).toContain('left: 50%')
  })
})
