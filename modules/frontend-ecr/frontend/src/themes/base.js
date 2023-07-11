import light from './light';
import dark from './dark';

const themes = {
  light,
  dark,
};

export default function getTheme(theme) {
  return themes[theme];
}
