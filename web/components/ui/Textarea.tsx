type TextareaProps = {
  label: string;
  name: string;
  defaultValue?: string;
  description?: string;
  example?: string;
  placeholder?: string;
  required?: boolean;
  rows?: number;
};

export default function Textarea({
  label,
  name,
  defaultValue,
  description,
  example,
  placeholder,
  required,
  rows = 4,
}: TextareaProps) {
  const displayLabel = label.replace(/\s*\*$/, "");

  return (
    <label className="block md:col-span-2">
      <span className="text-sm font-semibold text-slate-800">
        {required && <span className="text-red-500">* </span>}
        {displayLabel}
      </span>
      {!example && description && <span className="mt-1 block text-xs leading-5 text-slate-500">{description}</span>}
      <span className={example ? "mt-2 grid gap-3 lg:grid-cols-[minmax(0,1.2fr)_minmax(260px,0.8fr)]" : "block"}>
        <textarea
          className={`${example ? "" : "mt-2"} w-full resize-y rounded-md border border-slate-300 bg-white px-3.5 py-3 text-sm leading-6 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100`}
          defaultValue={defaultValue}
          name={name}
          placeholder={placeholder}
          required={required}
          rows={rows}
        />
        {example && (
          <span className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3">
            <strong className="block text-xs font-semibold text-slate-700">작성 방법</strong>
            <span className="mt-1 block text-xs leading-5 text-slate-500">{description}</span>
            <strong className="mt-3 block text-xs font-semibold text-slate-700">예시</strong>
            <span className="mt-1 block whitespace-pre-line text-xs leading-5 text-slate-500">{example}</span>
          </span>
        )}
      </span>
    </label>
  );
}
