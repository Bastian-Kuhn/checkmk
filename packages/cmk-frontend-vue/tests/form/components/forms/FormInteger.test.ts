import { fireEvent, render, screen } from '@testing-library/vue'
import FormInteger from '@/form/components/forms/FormInteger.vue'
import type * as FormSpec from '@/form/components/vue_formspec_components'
import { renderFormWithData } from '../cmk-form-helper'

const validators: FormSpec.Validator[] = [
  {
    type: 'number_in_range',
    min_value: 1,
    max_value: 100,
    error_message: 'Value must be between 1 and 100'
  }
]

const spec: FormSpec.Integer = {
  type: 'integer',
  title: 'fooTitle',
  help: 'fooHelp',
  validators: validators,
  label: 'fooLabel',
  unit: 'fooUnit',
  input_hint: 'fooInputHint'
}

test('FormInteger renders value', () => {
  render(FormInteger, {
    props: {
      spec,
      data: 42,
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(element.value).toBe('42')
})

test('FormInteger updates data', async () => {
  const { getCurrentData: currentData } = renderFormWithData({
    spec,
    data: 42,
    backendValidation: []
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  await fireEvent.update(element, '23')

  expect(currentData()).toBe('23')
})

test('FormInteger checks validators', async () => {
  render(FormInteger, {
    props: {
      spec,
      data: 42,
      backendValidation: []
    }
  })

  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  await fireEvent.update(element, '0')

  screen.getByText('Value must be between 1 and 100')
})

test('FormInteger renders backend validation messages', async () => {
  render(FormInteger, {
    props: {
      spec,
      data: 42,
      backendValidation: [
        {
          location: [],
          message: 'Backend error message',
          invalid_value: 12
        }
      ]
    }
  })

  await screen.findByText('Backend error message')
  const element = screen.getByRole<HTMLInputElement>('spinbutton', { name: 'fooLabel' })
  expect(element.value).toBe('12')
})
