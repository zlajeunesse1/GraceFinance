import { useState } from 'react'
import { useTheme } from '../context/ThemeContext'

export default function Input(props) {
  var focused = useState(false)
  var isFocused = focused[0]
  var setFocused = focused[1]
  var ctx = useTheme()
  var theme = ctx.theme

  return (
    <div className="mb-4">
      {props.label && (
        <label className="block text-sm font-medium mb-1.5" style={{ color: theme.muted }}>
          {props.label}
        </label>
      )}
      <div className="relative">
        {props.icon && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm" style={{ color: theme.muted }}>
            {props.icon}
          </span>
        )}
        <input
          type={props.type || 'text'}
          value={props.value}
          onChange={props.onChange}
          placeholder={props.placeholder}
          onFocus={function () { setFocused(true) }}
          onBlur={function () { setFocused(false) }}
          className="w-full rounded-xl text-sm outline-none transition-all duration-200"
          style={{
            padding: props.icon ? '12px 14px 12px 36px' : '12px 14px',
            background: theme.input,
            border: '1.5px solid ' + (props.error ? theme.error : isFocused ? theme.accent : theme.border),
            color: theme.text,
          }}
        />
      </div>
      {props.error && (
        <p className="text-xs mt-1" style={{ color: theme.error }}>{props.error}</p>
      )}
    </div>
  )
}
