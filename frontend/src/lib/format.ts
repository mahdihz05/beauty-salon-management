export const faNumber = new Intl.NumberFormat("fa-IR");

export function toman(value: number) {
  return `${faNumber.format(value)} تومان`;
}
