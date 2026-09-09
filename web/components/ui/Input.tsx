type InputProps = {
  label: string;
  type?: string;
  placeholder?: string;
  name?: string;
  autoComplete?: string;
  defaultValue?: string | number;
  minLength?: number;
  required?: boolean;
  showRequiredMark?: boolean;
  value?: string | number;
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
};

export default function Input({
  label,
  type = "text",
  placeholder,
  name,
  autoComplete,
  defaultValue,
  minLength,
  required,
  showRequiredMark = false,
  value,
  onChange,
}: InputProps) {
  const displayLabel = label.replace(/\s*\*$/, "");

  return (
    <label className="block">
      <span className="text-sm font-semibold text-slate-800">
        {required && showRequiredMark && <span className="text-red-500">* </span>}
        {displayLabel}
      </span>
      <input
        autoComplete={autoComplete}
        className="mt-2 h-11 w-full rounded-md border border-slate-300 bg-white px-3.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        defaultValue={defaultValue}
        minLength={minLength}
        name={name}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        type={type}
        value={value}
      />
    </label>
  );
}
