// ABOUTME: react-native-marked renderer that disables font scaling on every text node it
// ABOUTME: produces — the library renders via RN's own Text, bypassing our Text wrapper.

import { Linking, Text as RNText, View, type TextStyle, type ViewStyle } from 'react-native';
import { Renderer } from 'react-native-marked';
import type { ReactNode } from 'react';

export class NoScaleRenderer extends Renderer {
  private textKeyCounter = 0;

  private createTextNode(children: string | ReactNode[], styles?: TextStyle): ReactNode {
    return (
      <RNText key={`no-scale-${this.textKeyCounter++}`} selectable allowFontScaling={false} style={styles}>
        {children}
      </RNText>
    );
  }

  text(text: string | ReactNode[], styles?: TextStyle): ReactNode {
    return this.createTextNode(text, styles);
  }

  strong(children: string | ReactNode[], styles?: TextStyle): ReactNode {
    return this.createTextNode(children, styles);
  }

  em(children: string | ReactNode[], styles?: TextStyle): ReactNode {
    return this.createTextNode(children, styles);
  }

  del(children: string | ReactNode[], styles?: TextStyle): ReactNode {
    return this.createTextNode(children, styles);
  }

  codespan(text: string, styles?: TextStyle): ReactNode {
    return this.createTextNode(text, styles);
  }

  escape(text: string, styles?: TextStyle): ReactNode {
    return this.createTextNode(text, styles);
  }

  heading(text: string | ReactNode[], styles?: TextStyle): ReactNode {
    return this.createTextNode(text, styles);
  }

  html(text: string | ReactNode[], styles?: TextStyle): ReactNode {
    return this.createTextNode(text, styles);
  }

  br(): ReactNode {
    return this.createTextNode('\n', {});
  }

  link(children: string | ReactNode[], href: string, styles?: TextStyle): ReactNode {
    return (
      <RNText
        key={`no-scale-link-${this.textKeyCounter++}`}
        selectable
        allowFontScaling={false}
        accessibilityRole="link"
        style={styles}
        onPress={() => Linking.openURL(href)}
      >
        {children}
      </RNText>
    );
  }

  paragraph(children: ReactNode[], styles?: ViewStyle): ReactNode {
    return (
      <View key={`no-scale-p-${this.textKeyCounter++}`} style={styles}>
        {children}
      </View>
    );
  }

  listItem(children: ReactNode[], styles?: ViewStyle): ReactNode {
    return (
      <View key={`no-scale-li-${this.textKeyCounter++}`} style={styles}>
        {children}
      </View>
    );
  }

  blockquote(children: ReactNode[], styles?: ViewStyle): ReactNode {
    return (
      <View key={`no-scale-bq-${this.textKeyCounter++}`} style={styles}>
        {children}
      </View>
    );
  }

  code(text: string, _language?: string, _containerStyle?: ViewStyle, textStyle?: TextStyle): ReactNode {
    return this.createTextNode(text, textStyle);
  }
}
