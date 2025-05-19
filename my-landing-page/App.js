import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Video } from 'expo-video';
import Constants from 'expo-constants';

const apiKey = Constants.expoConfig.extra.googleApiKey;

console.log("Google API Key:", apiKey);

GOOGLE_API_KEY=your-secure-google-api-key-here


export default function App() {
  return (
    <View style={styles.container}>
      <Video
        source={require('.assets\vid\background.mp4')} // Add your video to /assets
        style={StyleSheet.absoluteFill}
        resizeMode="cover"
        isMuted
        isLooping
        shouldPlay
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  overlay: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  logo: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 30,
    textTransform: 'uppercase',
    lineHeight: 20,
  },
  heading: {
    color: '#fff',
    fontSize: 26,
    fontWeight: 'bold',
    marginBottom: 20,
    lineHeight: 36,
  },
  description: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '500',
    lineHeight: 22,
    marginBottom: 40,
  },
  button: {
    borderColor: '#fff',
    borderWidth: 1.5,
    paddingVertical: 12,
    paddingHorizontal: 30,
    borderRadius: 30,
    alignSelf: 'flex-start',
  },
  buttonText: {
    color: '#fff',
    fontWeight: 'bold',
    letterSpacing: 1,
  },
});
