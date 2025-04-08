import React from 'react';
import { StyleSheet, Text, View, TouchableOpacity } from 'react-native';
import { Video } from 'expo-av';

import { StatusBar } from 'react-native';

export default function App() {
  return (
    <View style={styles.container}>
      <Video
        source={require('./assets/vid/background.mp4')}
        style={StyleSheet.absoluteFill}
        muted={true}
        resizeMode="cover"
        repeat={true}
        paused={false}
      />
      <View style={styles.overlay}>
        <Text style={styles.logo}>YOUR LIFE,{"\n"}YOUR BUILD</Text>
        <Text style={styles.heading}>
          Navigating life isn't easy,{"\n"}but you don't have to do it alone.
        </Text>
        <Text style={styles.description}>
          In our technology, we talk about how we{"\n"}can become better, happier, and healthier.
        </Text>
        <TouchableOpacity style={styles.button}>
          <Text style={styles.buttonText}>SUBSCRIBE</Text>
        </TouchableOpacity>
      </View>
      <StatusBar barStyle="light-content" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    paddingHorizontal: 24,
    paddingVertical: 60,
    justifyContent: 'center',
  },
  logo: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
    textTransform: 'uppercase',
    marginBottom: 30,
  },
  heading: {
    color: 'white',
    fontSize: 26,
    fontWeight: 'bold',
    lineHeight: 36,
    marginBottom: 20,
  },
  description: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 22,
    marginBottom: 40,
  },
  button: {
    borderWidth: 1.5,
    borderColor: 'white',
    borderRadius: 30,
    paddingVertical: 12,
    paddingHorizontal: 30,
    alignSelf: 'flex-start',
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    letterSpacing: 1,
  },
});
